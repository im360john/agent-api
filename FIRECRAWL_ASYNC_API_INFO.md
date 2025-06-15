# Firecrawl Async Crawl API Information

## Summary

Yes, Firecrawl does have async crawl API capabilities! Here's what I found:

## 1. Async Crawl Method: `async_crawl_url()`

The Firecrawl package includes an `async_crawl_url()` method that starts an asynchronous crawl job.

### Method Signature
```python
async_crawl_url(self, url: str, *, 
    include_paths: Optional[List[str]] = None,
    exclude_paths: Optional[List[str]] = None, 
    max_depth: Optional[int] = None,
    max_discovery_depth: Optional[int] = None,
    limit: Optional[int] = None,
    allow_backward_links: Optional[bool] = None,
    allow_external_links: Optional[bool] = None,
    ignore_sitemap: Optional[bool] = None,
    scrape_options: Optional[ScrapeOptions] = None,
    webhook: Union[str, WebhookConfig, None] = None,
    deduplicate_similar_urls: Optional[bool] = None,
    ignore_query_parameters: Optional[bool] = None,
    regex_on_full_url: Optional[bool] = None,
    delay: Optional[int] = None,
    idempotency_key: Optional[str] = None,
    **kwargs
) -> CrawlResponse
```

### Returns
- `CrawlResponse` object with:
  - `success` - Whether crawl started successfully
  - `id` - Unique identifier for the crawl job
  - `url` - Status check URL for the crawl
  - `error` - Error message if start failed

## 2. Status Polling: `check_crawl_status()`

You can poll for results while crawling is in progress using the `check_crawl_status()` method.

### Method Signature
```python
check_crawl_status(self, id: str) -> CrawlStatusResponse
```

### Returns
- `CrawlStatusResponse` containing:
  - **Status Information:**
    - `status` - Current state (scraping/completed/failed/cancelled)
    - `completed` - Number of pages crawled
    - `total` - Total pages to crawl
    - `creditsUsed` - API credits consumed
    - `expiresAt` - Data expiration timestamp
  - **Results:**
    - `data` - List of crawled documents
    - `next` - URL for next page of results (if paginated)
    - `success` - Whether status check succeeded
    - `error` - Error message if failed

## 3. Incremental Results

Yes, you can get incremental results as pages are crawled! When you call `check_crawl_status()`:
- The `data` field contains the list of documents crawled so far
- The `completed` field shows how many pages have been processed
- The `total` field shows the total number of pages to crawl
- You can poll periodically to get newly crawled pages

## 4. Current Implementation vs Async

The current implementation in `/home/john/repos/agent-api/agents/slack_treez_agent.py` uses the synchronous `crawl_url()` method with a `poll_interval` parameter:

```python
crawl_response = firecrawl.crawl_url(
    base_url, 
    limit=800,
    scrape_options=ScrapeOptions(
        formats=['markdown'],
        maxAge=172800  # Use cache if less than 48 hours old
    )
)
```

This method internally polls and waits for the entire crawl to complete before returning all results.

## 5. Example Async Implementation

Here's how you could modify the code to use async crawling with incremental results:

```python
# Start async crawl
crawl_job = firecrawl.async_crawl_url(
    base_url,
    limit=800,
    scrape_options=ScrapeOptions(
        formats=['markdown'],
        maxAge=172800
    )
)

# Check if crawl started successfully
if crawl_job.success:
    crawl_id = crawl_job.id
    processed_urls = set()
    
    # Poll for results
    while True:
        status = firecrawl.check_crawl_status(crawl_id)
        
        # Process new documents
        if status.data:
            for doc in status.data:
                url = doc.get('url') or doc.get('sourceURL')
                if url and url not in processed_urls:
                    # Process this new document
                    process_document(doc)
                    processed_urls.add(url)
        
        # Check if crawl is complete
        if status.status in ['completed', 'failed', 'cancelled']:
            break
            
        # Log progress
        logger.info(f"Crawl progress: {status.completed}/{status.total} pages")
        
        # Wait before next poll
        await asyncio.sleep(5)  # Poll every 5 seconds
```

## Other Async Methods Available

Firecrawl also provides these async methods:
- `async_batch_scrape_urls()` - Batch scrape multiple URLs asynchronously
- `async_deep_research()` - Perform deep research asynchronously
- `async_extract()` - Extract data asynchronously
- `async_generate_llms_text()` - Generate text with LLMs asynchronously

Each has corresponding status check methods:
- `check_batch_scrape_status()`
- `check_deep_research_status()`
- `get_extract_status()`
- `check_generate_llms_text_status()`