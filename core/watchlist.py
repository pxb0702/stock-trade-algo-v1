"""
Watchlist Management Module
Supports persistent JSON storage, dynamic addition, deletion,
and auto-resolution of Chinese stock/ETF names.
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from config import DEFAULT_WATCHLIST
from core.data_feed import resolve_stock_name, get_market_prefix, is_valid_chinese_name, COMMON_NAMES

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.json")


def sanitize_watchlist_items(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Ensure each watchlist item has the strictly correct, official Chinese stock/ETF name.
    Fixes cases where code and name were mismatched (e.g. 510500 named 招商银行 or 600036 named 60003).
    """
    modified = False
    clean_items = []
    seen_codes = set()

    for item in items:
        if not isinstance(item, dict):
            modified = True
            continue
        code = "".join(filter(str.isdigit, str(item.get("code", ""))))
        if len(code) != 6:
            # Drop invalid code length
            modified = True
            continue
        if code in seen_codes:
            # Drop duplicate code
            modified = True
            continue
        seen_codes.add(code)

        cur_name = str(item.get("name", "")).strip()
        official_name = resolve_stock_name(code)

        target_name = cur_name
        # Auto-correction conditions:
        # 1. cur_name is purely digits (e.g. "60003") or not a valid Chinese name
        # 2. cur_name equals code
        # 3. official_name is known and cur_name belongs to a different stock in COMMON_NAMES
        if official_name:
            if not is_valid_chinese_name(cur_name) or cur_name == code:
                target_name = official_name
                modified = True
            elif cur_name != official_name:
                # Check if cur_name belongs to another stock in COMMON_NAMES (e.g. "招商银行" on "510500")
                is_other_stock_name = any(c != code and n == cur_name for c, n in COMMON_NAMES.items())
                if is_other_stock_name or code in COMMON_NAMES:
                    target_name = official_name
                    modified = True
        elif not is_valid_chinese_name(cur_name):
            target_name = f"标的 {code}"
            modified = True

        market = str(item.get("market") or get_market_prefix(code).upper()).upper()
        desc = item.get("desc") or f"A股 {target_name} ({code})"

        # If desc had mismatched name like "A股 招商银行 (510500)", fix it
        if target_name != cur_name and ("A股 " in desc or f"({code})" in desc):
            desc = f"A股 {target_name} ({code})"
            modified = True

        clean_items.append({
            "code": code,
            "name": target_name,
            "market": market,
            "desc": desc
        })

    return clean_items, modified


def load_watchlist() -> List[Dict[str, Any]]:
    """Load user watchlist from persistent JSON file, or initialize with defaults."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    cleaned_items, modified = sanitize_watchlist_items(data)
                    if modified:
                        save_watchlist(cleaned_items)
                    return cleaned_items
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
    Validates strictly 6-digit A-share/ETF codes and resolves the authentic name,
    preventing code/name mismatches.
    """
    clean_code = "".join(filter(str.isdigit, str(code)))
    if len(clean_code) != 6:
        return False, "请输入有效的6位A股或ETF代码 (如 600036, 000333, 510500)", None
        
    current_list = load_watchlist()
    
    # Check if already present
    for item in current_list:
        if item.get("code") == clean_code:
            return False, f"标的 {clean_code} ({item.get('name')}) 已在自选列表中", item
            
    official_name = resolve_stock_name(clean_code)
    
    # Authoritative name resolution
    resolved_name = ""
    if official_name:
        resolved_name = official_name
    elif name and is_valid_chinese_name(name):
        resolved_name = name.strip()
    else:
        resolved_name = f"标的 {clean_code}"

    # If user provided a name, but it's another known stock's name (e.g. 招商银行 for 510500), enforce official_name!
    if name and is_valid_chinese_name(name) and official_name:
        is_other_stock_name = any(c != clean_code and n == name.strip() for c, n in COMMON_NAMES.items())
        if is_other_stock_name:
            resolved_name = official_name
        
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
