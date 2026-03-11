
# Database configuration - update with your credentials
'''
DB_CONFIG = {
    'host': os.getenv('HOST', 'edx.mysleepwell.com'),
    'database': os.getenv('MYSQL_DATABASE', 'openedx'),
    'user': os.getenv('MYSQL_USER', 'openedx'),
    'password': os.getenv('MYSQL_PASSWORD', '9gEi7luQ'),
    'port': os.getenv('MYSQL_PORT', 3306),
}

'''

from fastapi import APIRouter,Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

htmlrouter = APIRouter()



@htmlrouter.get("/users/", tags=["users"])

# Health check endpoint
@htmlrouter.get("/reportui")
async def read_item(request: Request,):
    return templates.TemplateResponse(
        request=request, name="report1.html",
    )

@htmlrouter.get("/reportui3")
async def read_item(request: Request,):
    return templates.TemplateResponse(
        request=request, name="asm_dashboard03.html",
    )

@htmlrouter.get("/reportui4")
async def read_item(request: Request,):
    return templates.TemplateResponse(
        request=request, name="asm_dashboard04.html",
    )

@htmlrouter.get("/reportui5")
async def read_item(request: Request,):
    return templates.TemplateResponse(
        request=request, name="asm_dashboard05.html",
    )