# Competitive Pricing UI Deployment Guide

## Running the Chat Interface

### Local Development

1. **Install AG UI requirements** (if not already installed):
```bash
pip install agno[ag-ui]
```

2. **Run the UI application**:
```bash
python app_competitive_pricing.py
```

3. **Access the interface**:
- Open browser to: http://localhost:7100
- The chat interface will load automatically

### Production Deployment

#### Option 1: Docker Deployment

Create a `Dockerfile.ui`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt agno[ag-ui]

# Copy application files
COPY . .

# Expose port
EXPOSE 7100

# Run the UI
CMD ["python", "app_competitive_pricing.py"]
```

Build and run:
```bash
docker build -f Dockerfile.ui -t pricing-ui .
docker run -p 7100:7100 --env-file .env pricing-ui
```

#### Option 2: Process Manager (PM2)

```bash
# Install PM2
npm install -g pm2

# Start the UI
pm2 start app_competitive_pricing.py --interpreter python3 --name pricing-ui

# Save PM2 config
pm2 save
pm2 startup
```

#### Option 3: Systemd Service

Create `/etc/systemd/system/pricing-ui.service`:
```ini
[Unit]
Description=Competitive Pricing UI
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/agent-api
Environment="PATH=/home/ubuntu/.local/bin:/usr/bin"
EnvironmentFile=/home/ubuntu/agent-api/.env
ExecStart=/usr/bin/python3 /home/ubuntu/agent-api/app_competitive_pricing.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable pricing-ui
sudo systemctl start pricing-ui
```

### Environment Variables

Make sure these are set:
```bash
# Database
DB_HOST=your-db-host
DB_PORT=5432
DB_DATABASE=your-db
DB_USER=your-user
DB_PASS=your-password

# OpenAI
OPENAI_API_KEY=your-openai-key

# Scraping APIs
FIRECRAWL_API_KEY=your-firecrawl-key
BROWSERBASE_API_KEY=your-browserbase-key
EXA_API_KEY=your-exa-key
```

### Nginx Configuration (Optional)

For production, proxy through Nginx:

```nginx
server {
    listen 80;
    server_name pricing.yourdomain.com;

    location / {
        proxy_pass http://localhost:7100;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Security Considerations

1. **Authentication**: AG UI doesn't include auth by default. Add authentication:
   - Use Nginx basic auth
   - Add OAuth2 proxy
   - Implement custom auth in the app

2. **HTTPS**: Always use HTTPS in production
   - Use Let's Encrypt for SSL certificates
   - Configure SSL in Nginx

3. **Rate Limiting**: Protect against abuse
   - Configure Nginx rate limiting
   - Add API rate limits

### Monitoring

1. **Health Check Endpoint**:
```python
@app.route("/health")
async def health():
    return {"status": "healthy", "agent": "active"}
```

2. **Logs**:
```bash
# View logs
pm2 logs pricing-ui

# Or with systemd
journalctl -u pricing-ui -f
```

3. **Metrics**: Consider adding:
- Prometheus metrics
- Application performance monitoring (APM)
- Error tracking (Sentry)

### Scaling

For high traffic:

1. **Multiple Instances**:
```bash
# Run multiple instances with PM2
pm2 start app_competitive_pricing.py -i 4
```

2. **Load Balancer**: Use Nginx to balance between instances

3. **Database Pooling**: Already configured in the agent

### Troubleshooting

Common issues:

1. **Port already in use**:
```bash
# Find process using port 7100
lsof -i :7100
# Kill if needed
kill -9 <PID>
```

2. **Database connection errors**:
- Check environment variables
- Verify database is accessible
- Check firewall rules

3. **Memory issues**:
- Monitor with: `pm2 monit`
- Increase memory limit if needed

### Features in the UI

The chat interface provides:

1. **Main Chat**: Natural language interaction
2. **Quick Actions**: Pre-defined commands in sidebar
3. **Markdown Rendering**: Tables and formatted responses
4. **Confidence Indicators**: Visual feedback on data reliability
5. **Real-time Updates**: WebSocket support for live data

### Customization

To customize the UI further:

1. Edit `app_competitive_pricing.py`:
   - Change colors/theme
   - Add more quick actions
   - Modify welcome message

2. Advanced customization:
   - Fork AG UI repository
   - Build custom frontend
   - Use AG UI API directly