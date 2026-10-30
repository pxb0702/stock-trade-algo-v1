"""
Watchlist Management Module
Supports persistent JSON storage, dynamic addition, deletion,
and auto-resolution of Chinese stock/ETF names.
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from config import DEFAULT_WATCHLIST
from core.data_feed import resolve_stock_name, get_market_prefix

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.json")


def load_watchlist() -> List[Dict[str, Any]]:
    """Load user watchlist from persistent JSON file, or initialize with defaults."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception as e:
            print(f"[Watchlist] Error reading {WATCHLIST_FILE}: {e}")
            
    # Default initialization
    save_watchlist(DEFAULT_WATCHLIST)
    return list(DEFAULT_WATCHLIST)


def save_watchlist(items: List[Dict[str, Any]]) -> bool:
    """Save user watchlist to persistent JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[Watchlist] Error writing {WATCHLIST_FILE}: {e}")
        return False


def add_stock_to_watchlist(code: str, name: Optional[str] = None, desc: str = "") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Add a new stock or ETF to watchlist.
    Automatically resolves stock name if not explicitly provided.
    """
    clean_code = "".join(filter(str.isdigit, str(code)))
    if not clean_code or len(clean_code) < 5:
        return False, "请输入有效的5~6位股票或ETF代码", None
        
    current_list = load_watchlist()
    
    # Check if already present
    for item in current_list:
        if item.get("code") == clean_code:
            return False, f"标的 {clean_code} ({item.get('name')}) 已在自选列表中", item
            
    # Auto-resolve stock name if needed
    if not name or name.strip() == clean_code:
        resolved_name = resolve_stock_name(clean_code)
    else:
        resolved_name = name.strip()
        
    market_pfx = get_market_prefix(clean_code).upper()
    
    new_item = {
        "code": clean_code,
        "name": resolved_name,
        "market": market_pfx,
        "desc": desc.strip() or f"A股 {resolved_name} ({clean_code})"
    }
    
    current_list.append(new_item)
    if save_watchlist(current_list):
        return True, f"成功添加 {resolved_name} ({clean_code}) 到自选列表", new_item
    else:
        return False, "保存自选列表文件失败", None


def remove_stock_from_watchlist(code: str) -> Tuple[bool, str]:
    """Remove a stock or ETF from user's watchlist."""
    clean_code = "".join(filter(str.isdigit, str(code)))
    current_list = load_watchlist()
    
    initial_len = len(current_list)
    new_list = [item for item in current_list if item.get("code") != clean_code]
    
    if len(new_list) == initial_len:
        return False, f"未在自选列表中找到标的 {clean_code}"
        
    if save_watchlist(new_list):
        return True, f"已将标的 {clean_code} 从自选列表移除"
    else:
        return False, "保存自选列表失败"


def reset_watchlist_to_default() -> List[Dict[str, Any]]:
    """Reset watchlist back to the built-in default list."""
    save_watchlist(DEFAULT_WATCHLIST)
    return list(DEFAULT_WATCHLIST)
