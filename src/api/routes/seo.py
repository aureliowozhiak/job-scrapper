"""SEO and web standards routes."""
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from src.database.connection import get_db
from src.database.repositories import PositionRepository
from src.core.config import settings

router = APIRouter()


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt(request: Request):
    """Serve robots.txt for web crawlers."""
    base_url = str(request.base_url).rstrip('/')
    robots_content = f"""# robots.txt for Job Scrapper Pro
User-agent: *
Allow: /
Allow: /api/jobs/
Allow: /browse
Disallow: /api/admin/
Disallow: /api/health/
Disallow: /ws

# Sitemap
Sitemap: {base_url}/sitemap.xml

# Crawl-delay for politeness
Crawl-delay: 1
"""
    return robots_content


@router.get("/sitemap.xml", response_class=Response)
async def sitemap_xml(request: Request, db: Session = Depends(get_db)):
    """Generate sitemap.xml for SEO."""
    base_url = str(request.base_url).rstrip('/')
    
    # Create root element
    urlset = Element('urlset')
    urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    
    # Add main pages
    pages = [
        {'loc': '/', 'priority': '1.0', 'changefreq': 'daily'},
        {'loc': '/browse', 'priority': '0.9', 'changefreq': 'daily'},
        {'loc': '/api/docs', 'priority': '0.5', 'changefreq': 'monthly'},
    ]
    
    for page in pages:
        url = SubElement(urlset, 'url')
        loc = SubElement(url, 'loc')
        loc.text = f"{base_url}{page['loc']}"
        
        lastmod = SubElement(url, 'lastmod')
        lastmod.text = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        changefreq = SubElement(url, 'changefreq')
        changefreq.text = page['changefreq']
        
        priority = SubElement(url, 'priority')
        priority.text = page['priority']
    
    # Add job listings (sample, not all to keep sitemap size reasonable)
    repo = PositionRepository(db)
    recent_jobs = repo.get_all(limit=500, offset=0)
    
    for job in recent_jobs:
        url = SubElement(urlset, 'url')
        
        loc = SubElement(url, 'loc')
        loc.text = f"{base_url}/browse?job_id={job.id}"
        
        lastmod = SubElement(url, 'lastmod')
        lastmod.text = job.created_at.strftime('%Y-%m-%d') if job.created_at else datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        changefreq = SubElement(url, 'changefreq')
        changefreq.text = 'weekly'
        
        priority = SubElement(url, 'priority')
        priority.text = '0.8'
    
    xml_content = tostring(urlset, encoding='unicode', method='xml')
    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    
    return Response(
        content=xml_declaration + xml_content,
        media_type='application/xml'
    )


@router.get("/rss.xml", response_class=Response)
async def rss_feed(
    limit: int = 50,
    db: Session = Depends(get_db),
    request: Request = None
):
    """Generate RSS feed for recent jobs."""
    base_url = str(request.base_url).rstrip('/')
    
    repo = PositionRepository(db)
    recent_jobs = repo.get_all(limit=limit, offset=0)
    
    # Create RSS feed
    rss = Element('rss')
    rss.set('version', '2.0')
    rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')
    
    channel = SubElement(rss, 'channel')
    
    # Channel metadata
    title = SubElement(channel, 'title')
    title.text = 'Job Scrapper Pro - Recent Remote Jobs'
    
    link = SubElement(channel, 'link')
    link.text = base_url
    
    description = SubElement(channel, 'description')
    description.text = 'Latest remote job opportunities from multiple job boards'
    
    language = SubElement(channel, 'language')
    language.text = 'en-us'
    
    lastBuildDate = SubElement(channel, 'lastBuildDate')
    lastBuildDate.text = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    # Atom self link
    atom_link = SubElement(channel, 'atom:link')
    atom_link.set('href', f'{base_url}/rss.xml')
    atom_link.set('rel', 'self')
    atom_link.set('type', 'application/rss+xml')
    
    # Add job items
    for job in recent_jobs:
        item = SubElement(channel, 'item')
        
        item_title = SubElement(item, 'title')
        item_title.text = job.title
        
        item_link = SubElement(item, 'link')
        item_link.text = job.link
        
        item_description = SubElement(item, 'description')
        desc_text = f"Company: {job.company}"
        if job.source:
            desc_text += f" | Source: {job.source}"
        item_description.text = desc_text
        
        item_pubDate = SubElement(item, 'pubDate')
        pub_date = job.created_at if job.created_at else datetime.now(timezone.utc)
        item_pubDate.text = pub_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        item_guid = SubElement(item, 'guid')
        item_guid.set('isPermaLink', 'false')
        item_guid.text = f"{base_url}/jobs/{job.id}"
        
        if job.source:
            item_category = SubElement(item, 'category')
            item_category.text = job.source
    
    xml_content = tostring(rss, encoding='unicode', method='xml')
    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    
    return Response(
        content=xml_declaration + xml_content,
        media_type='application/rss+xml'
    )


@router.get("/manifest.json")
async def manifest_json():
    """Serve PWA manifest."""
    return {
        "name": "Job Scrapper Pro",
        "short_name": "JobScrapper",
        "description": "Modern job scraping application for remote positions",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#1a202c",
        "theme_color": "#3b82f6",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": "/static/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "/static/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ],
        "categories": ["productivity", "business"],
        "shortcuts": [
            {
                "name": "Search Jobs",
                "short_name": "Search",
                "description": "Search for remote jobs",
                "url": "/?tab=job-feed",
                "icons": [{"src": "/static/icon-search-96.png", "sizes": "96x96"}]
            },
            {
                "name": "Task Manager",
                "short_name": "Tasks",
                "description": "Manage scraping tasks",
                "url": "/?tab=task-manager",
                "icons": [{"src": "/static/icon-task-96.png", "sizes": "96x96"}]
            }
        ]
    }
