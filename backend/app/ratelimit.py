"""Shared rate limiter (slowapi). Kept in its own module to avoid a circular
import between main.py and the routers that decorate their endpoints."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
