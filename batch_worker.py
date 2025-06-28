#!/usr/bin/env python3
"""
Background worker for processing batch pricing jobs.

This would typically run as a separate process/container in production,
processing jobs from a queue (Redis, RabbitMQ, etc).
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import json

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.competitive_pricing_agent import CompetitorPricingTools
from db.session import db_url


class BatchWorker:
    """Worker for processing batch pricing jobs"""
    
    def __init__(self):
        self.engine = create_engine(db_url.replace('+asyncpg', '').replace('+aiopg', ''), poolclass=NullPool)
        self.Session = sessionmaker(bind=self.engine)
        self.pricing_tools = CompetitorPricingTools(db_url)
        
    async def process_jobs(self):
        """Main loop to process pending jobs"""
        print("🔄 Batch worker started...")
        
        while True:
            try:
                # Get next pending job
                job = self.get_next_job()
                
                if job:
                    await self.process_job(job)
                else:
                    # No jobs, wait a bit
                    await asyncio.sleep(5)
                    
            except Exception as e:
                print(f"❌ Worker error: {e}")
                await asyncio.sleep(10)
    
    def get_next_job(self):
        """Get the next pending job from the queue"""
        with self.Session() as session:
            # Get oldest pending job
            result = session.execute(text("""
                UPDATE pricing.batch_jobs
                SET status = 'running'::pricing.batch_job_status,
                    started_at = CURRENT_TIMESTAMP
                WHERE id = (
                    SELECT id FROM pricing.batch_jobs
                    WHERE status = 'pending'
                    ORDER BY created_at
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id, name, metadata
            """))
            
            job = result.fetchone()
            if job:
                session.commit()
                return {"id": job[0], "name": job[1], "metadata": json.loads(job[2])}
            
            return None
    
    async def process_job(self, job):
        """Process a single batch job"""
        job_id = job['id']
        print(f"📋 Processing job: {job['name']} ({job_id})")
        
        try:
            # Get all job items
            with self.Session() as session:
                items = session.execute(text("""
                    SELECT bji.id, bji.product_id, bji.competitor_id,
                           p.name as product_name, p.brand, p.metadata as product_meta,
                           c.name as competitor_name, c.urls
                    FROM pricing.batch_job_items bji
                    JOIN pricing.products p ON bji.product_id = p.id
                    JOIN pricing.competitors c ON bji.competitor_id = c.id
                    WHERE bji.batch_job_id = :job_id
                    AND bji.status = 'pending'
                """), {"job_id": job_id})
                
                items_list = items.fetchall()
                total_items = len(items_list)
                
                print(f"📊 Found {total_items} items to process")
                
                # Process each item
                for i, item in enumerate(items_list):
                    item_id, prod_id, comp_id, prod_name, brand, prod_meta, comp_name, comp_urls = item
                    
                    try:
                        # Check if we need fresh data
                        needs_update = self.check_needs_update(prod_id, comp_id, session)
                        
                        if needs_update:
                            # Scrape fresh data
                            print(f"🔍 Scraping {brand} {prod_name} at {comp_name} ({i+1}/{total_items})")
                            
                            search_query = f"{brand} {prod_name}"
                            scraped_data = await self.pricing_tools._scrape_competitor_price(
                                comp_name, comp_urls[0], search_query, 
                                json.loads(prod_meta) if prod_meta else {}
                            )
                            
                            if scraped_data:
                                # Store result
                                session.execute(text("""
                                    INSERT INTO pricing.price_history 
                                    (product_id, competitor_id, price, member_price, 
                                     availability_status, url, scraper_used, raw_data)
                                    VALUES (:product_id, :competitor_id, :price, :member_price, 
                                            :status, :url, 'batch_worker', :raw_data)
                                """), {
                                    "product_id": prod_id,
                                    "competitor_id": comp_id,
                                    "price": scraped_data.price,
                                    "member_price": scraped_data.member_price,
                                    "status": scraped_data.availability_status,
                                    "url": scraped_data.url,
                                    "raw_data": json.dumps(scraped_data.raw_data)
                                })
                            else:
                                # Not found
                                session.execute(text("""
                                    INSERT INTO pricing.price_history 
                                    (product_id, competitor_id, availability_status, url, scraper_used)
                                    VALUES (:product_id, :competitor_id, 'not_carried', :url, 'batch_worker')
                                """), {
                                    "product_id": prod_id,
                                    "competitor_id": comp_id,
                                    "url": comp_urls[0]
                                })
                        else:
                            print(f"✅ Using cached data for {brand} {prod_name} at {comp_name}")
                        
                        # Mark item as completed
                        session.execute(text("""
                            UPDATE pricing.batch_job_items
                            SET status = 'completed'::pricing.batch_job_status,
                                processed_at = CURRENT_TIMESTAMP
                            WHERE id = :item_id
                        """), {"item_id": item_id})
                        
                        session.commit()
                        
                        # Update job progress
                        self.update_job_progress(job_id)
                        
                        # Small delay to avoid overwhelming scrapers
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        print(f"❌ Error processing item {item_id}: {e}")
                        
                        # Mark item as failed
                        session.execute(text("""
                            UPDATE pricing.batch_job_items
                            SET status = 'failed'::pricing.batch_job_status,
                                processed_at = CURRENT_TIMESTAMP,
                                error_message = :error
                            WHERE id = :item_id
                        """), {"item_id": item_id, "error": str(e)})
                        
                        session.commit()
                        self.update_job_progress(job_id)
                
                # Job completed
                self.complete_job(job_id)
                print(f"✅ Job {job_id} completed!")
                
        except Exception as e:
            print(f"❌ Job {job_id} failed: {e}")
            self.fail_job(job_id, str(e))
    
    def check_needs_update(self, product_id, competitor_id, session):
        """Check if price data needs updating"""
        result = session.execute(text("""
            SELECT scraped_at FROM pricing.price_history
            WHERE product_id = :product_id 
            AND competitor_id = :competitor_id
            AND scraped_at > NOW() - INTERVAL '12 hours'
            ORDER BY scraped_at DESC
            LIMIT 1
        """), {"product_id": product_id, "competitor_id": competitor_id})
        
        return result.fetchone() is None
    
    def update_job_progress(self, job_id):
        """Update job progress"""
        with self.Session() as session:
            session.execute(text("SELECT pricing.update_batch_job_progress(:job_id)"), 
                          {"job_id": job_id})
            session.commit()
    
    def complete_job(self, job_id):
        """Mark job as completed"""
        with self.Session() as session:
            session.execute(text("""
                UPDATE pricing.batch_jobs
                SET status = 'completed'::pricing.batch_job_status,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = :job_id
            """), {"job_id": job_id})
            session.commit()
    
    def fail_job(self, job_id, error_message):
        """Mark job as failed"""
        with self.Session() as session:
            session.execute(text("""
                UPDATE pricing.batch_jobs
                SET status = 'failed'::pricing.batch_job_status,
                    completed_at = CURRENT_TIMESTAMP,
                    error_message = :error
                WHERE id = :job_id
            """), {"job_id": job_id, "error": error_message})
            session.commit()


async def main():
    """Run the batch worker"""
    worker = BatchWorker()
    await worker.process_jobs()


if __name__ == "__main__":
    # Run the worker
    asyncio.run(main())