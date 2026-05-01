# Thunder/utils/render_template.py

import asyncio
import html as html_module
import urllib.parse
import re

from jinja2 import Environment, FileSystemLoader
from pyrogram.errors import FloodWait

from Thunder import __version__
from Thunder.bot import StreamBot
from Thunder.server.exceptions import InvalidHash
from Thunder.utils.file_properties import get_fname, get_uniqid
from Thunder.utils.logger import logger
from Thunder.vars import Var

template_env = Environment(
    loader=FileSystemLoader('Thunder/template'),
    enable_async=True,
    cache_size=200,
    auto_reload=False,
    optimized=True
)

async def render_page(id: int, secure_hash: str, requested_action: str | None = None) -> str:
    try:
        try:
            message = await StreamBot.get_messages(chat_id=int(Var.BIN_CHANNEL), message_ids=id)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            message = await StreamBot.get_messages(chat_id=int(Var.BIN_CHANNEL), message_ids=id)
        
        if not message:
            raise InvalidHash("Message not found")
        
        file_unique_id = get_uniqid(message)
        file_name = get_fname(message)
        
        if not file_unique_id or file_unique_id[:6] != secure_hash:
            raise InvalidHash("File unique ID or secure hash mismatch during rendering.")
        
        quoted_filename = urllib.parse.quote(file_name.replace('/', '_'))
        src = urllib.parse.urljoin(Var.URL, f'{secure_hash}{id}/{quoted_filename}')
        safe_filename = html_module.escape(file_name)
        if requested_action == 'stream':
            template = template_env.get_template('req.html')
            markers = [int(m) for m in re.split(r'[,\s]+', Var.VIDEO_MIDROLL_MARKERS.strip()) if m.isdigit()]
            context = {
                'heading': f"View {safe_filename}",
                'file_name': safe_filename,
                'src': f"{src}?disposition=inline",
                'vast_ad_tag_url': Var.VIDEO_VAST_AD_TAG_URL,
                'midroll_markers': markers,
                'postroll_enabled': Var.VIDEO_POSTROLL_ENABLED,
                'banner_top_ad_code': Var.BANNER_TOP_AD_CODE,
                'banner_bottom_ad_code': Var.BANNER_BOTTOM_AD_CODE,
            }
        else:
            template = template_env.get_template('dl.html')
            context = {
                'file_name': safe_filename,
                'src': src,
                'direct_download_ad_url': Var.DIRECT_DOWNLOAD_AD_URL,
                'download_ad_cooldown_ms': Var.DOWNLOAD_AD_COOLDOWN_MS,
            }
        return await template.render_async(**context)
    except Exception as e:
        logger.error(f"Error in render_page for ID {id} and hash {secure_hash}: {e}", exc_info=True)
        raise


async def render_home_page(active_clients: int, total_workload: int, uptime: str) -> str:
    template = template_env.get_template('home.html')
    return await template.render_async(
        app_name=Var.NAME,
        version=__version__,
        uptime=uptime,
        active_clients=active_clients,
        total_workload=total_workload,
        repo_url='https://github.com/fyaz05/FileToLink',
    )
