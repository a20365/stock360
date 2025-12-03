from fastapi import APIRouter

from . import post

router = APIRouter()
router.include_router(post.router, tags=["POST"])
