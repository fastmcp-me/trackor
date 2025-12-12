from fastmcp import FastMCP
import os
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

BASE_DIR = os.getcwd()
DB_PATH = os.path.join(BASE_DIR, "expenses.db")
CATEGORIES_PATH = os.path.join(BASE_DIR, "categories.json")

mcp = FastMCP("ExpenseTracker")

def init_db():
    """Initialize database with necessary tables."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for faster date-based queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category)")

init_db()

@mcp.tool()
def add_expense(date: str, amount: float, category: str, subcategory: str = "", note: str = "") -> Dict[str, Any]:
    '''Add a new expense entry to the database.
    
    Args:
        date: Expense date (YYYY-MM-DD format)
        amount: Expense amount
        category: Main category (e.g., Food, Transportation)
        subcategory: Optional subcategory (e.g., Groceries, Restaurants)
        note: Optional note about the expense
    '''
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"}
    
    if amount <= 0:
        return {"status": "error", "message": "Amount must be positive"}
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            (date, amount, category, subcategory, note)
        )
        conn.commit()
        return {
            "status": "success", 
            "id": cursor.lastrowid,
            "message": f"Expense added successfully (ID: {cursor.lastrowid})"
        }

@mcp.tool()
def get_expense(expense_id: int) -> Dict[str, Any]:
    '''Get a specific expense by ID.'''
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT id, date, amount, category, subcategory, note FROM expenses WHERE id = ?",
            (expense_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            return {"status": "error", "message": f"Expense with ID {expense_id} not found"}
        
        cols = [description[0] for description in cursor.description]
        return {"status": "success", "expense": dict(zip(cols, row))}

@mcp.tool()
def list_expenses(
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    '''List expense entries with optional filters.
    
    Args:
        start_date: Start date filter (YYYY-MM-DD)
        end_date: End date filter (YYYY-MM-DD)
        category: Filter by category
        limit: Maximum number of records to return
    '''
    query = "SELECT id, date, amount, category, subcategory, note FROM expenses"
    conditions = []
    params = []
    
    if start_date:
        conditions.append("date >= ?")
        params.append(start_date)
    
    if end_date:
        conditions.append("date <= ?")
        params.append(end_date)
    
    if category:
        conditions.append("category = ?")
        params.append(category)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY date DESC, id DESC LIMIT ?"
    params.append(limit)
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(query, params)
        cols = [description[0] for description in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

@mcp.tool()
def update_expense(
    expense_id: int,
    date: Optional[str] = None,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    note: Optional[str] = None
) -> Dict[str, Any]:
    '''Update an existing expense entry.
    
    Args:
        expense_id: ID of expense to update
        date: New date (YYYY-MM-DD)
        amount: New amount
        category: New category
        subcategory: New subcategory
        note: New note
    '''
    # Check if expense exists
    current = get_expense(expense_id)
    if "error" in current.get("status", ""):
        return current
    
    # Build update query dynamically
    updates = []
    params = []
    
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
            updates.append("date = ?")
            params.append(date)
        except ValueError:
            return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"}
    
    if amount is not None:
        if amount <= 0:
            return {"status": "error", "message": "Amount must be positive"}
        updates.append("amount = ?")
        params.append(amount)
    
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    
    if subcategory is not None:
        updates.append("subcategory = ?")
        params.append(subcategory)
    
    if note is not None:
        updates.append("note = ?")
        params.append(note)
    
    if not updates:
        return {"status": "error", "message": "No fields to update"}
    
    # Add updated_at timestamp
    updates.append("updated_at = CURRENT_TIMESTAMP")
    
    # Add expense_id to params
    params.append(expense_id)
    
    query = f"UPDATE expenses SET {', '.join(updates)} WHERE id = ?"
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(query, params)
        conn.commit()
        
        if cursor.rowcount > 0:
            return {"status": "success", "message": f"Expense {expense_id} updated successfully"}
        else:
            return {"status": "error", "message": f"No expense found with ID {expense_id}"}

@mcp.tool()
def delete_expense(expense_id: int) -> Dict[str, Any]:
    '''Delete an expense entry by ID.'''
    # First check if it exists
    current = get_expense(expense_id)
    if "error" in current.get("status", ""):
        return current
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        
        if cursor.rowcount > 0:
            return {"status": "success", "message": f"Expense {expense_id} deleted successfully"}
        else:
            return {"status": "error", "message": f"Failed to delete expense {expense_id}"}

@mcp.tool()
def delete_expenses_by_date_range(start_date: str, end_date: str) -> Dict[str, Any]:
    '''Delete all expenses within a date range.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    '''
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"}
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "DELETE FROM expenses WHERE date BETWEEN ? AND ?",
            (start_date, end_date)
        )
        conn.commit()
        
        deleted_count = cursor.rowcount
        return {
            "status": "success", 
            "message": f"Deleted {deleted_count} expenses from {start_date} to {end_date}"
        }

@mcp.tool()
def summarize(
    start_date: str, 
    end_date: str, 
    category: Optional[str] = None,
    group_by_subcategory: bool = False
) -> List[Dict[str, Any]]:
    '''Summarize expenses within a date range.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        category: Optional category filter
        group_by_subcategory: If True, group by subcategory within category
    '''
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return [{"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"}]
    
    group_field = "category, subcategory" if group_by_subcategory else "category"
    select_field = "category, subcategory" if group_by_subcategory else "category"
    
    query = f"""
        SELECT {select_field}, 
               COUNT(*) as count, 
               SUM(amount) as total_amount,
               AVG(amount) as average_amount
        FROM expenses
        WHERE date BETWEEN ? AND ?
    """
    
    params = [start_date, end_date]
    
    if category:
        query += " AND category = ?"
        params.append(category)
    
    query += f" GROUP BY {group_field} ORDER BY total_amount DESC"
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(query, params)
        cols = [description[0] for description in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

@mcp.tool()
def get_statistics() -> Dict[str, Any]:
    '''Get overall expense statistics.'''
    with sqlite3.connect(DB_PATH) as conn:
        stats = {}
        
        # Total expenses
        cursor = conn.execute("SELECT COUNT(*), SUM(amount) FROM expenses")
        count, total = cursor.fetchone()
        stats["total_expenses"] = count
        stats["total_amount"] = total or 0
        
        # Average expense
        cursor = conn.execute("SELECT AVG(amount) FROM expenses")
        stats["average_expense"] = cursor.fetchone()[0] or 0
        
        # Most recent expense
        cursor = conn.execute("""
            SELECT date, amount, category 
            FROM expenses 
            ORDER BY date DESC, id DESC 
            LIMIT 1
        """)
        recent = cursor.fetchone()
        if recent:
            stats["most_recent"] = {
                "date": recent[0],
                "amount": recent[1],
                "category": recent[2]
            }
        
        # Expenses by month (current year)
        cursor = conn.execute("""
            SELECT strftime('%Y-%m', date) as month,
                   COUNT(*) as count,
                   SUM(amount) as total
            FROM expenses
            WHERE strftime('%Y', date) = strftime('%Y', 'now')
            GROUP BY strftime('%Y-%m', date)
            ORDER BY month DESC
        """)
        stats["monthly_summary"] = [
            {"month": row[0], "count": row[1], "total": row[2]}
            for row in cursor.fetchall()
        ]
        
        return {"status": "success", "statistics": stats}

@mcp.tool()
def export_expenses(format: str = "json") -> Dict[str, Any]:
    '''Export all expenses in specified format.
    
    Args:
        format: Export format - "json" or "csv"
    '''
    expenses = list_expenses(limit=10000)  # Get all expenses
    
    if format.lower() == "json":
        return {
            "status": "success",
            "format": "json",
            "data": json.dumps(expenses, indent=2),
            "count": len(expenses)
        }
    elif format.lower() == "csv":
        if not expenses:
            csv_data = "No expenses found"
        else:
            headers = expenses[0].keys()
            csv_lines = [",".join(headers)]
            for exp in expenses:
                csv_lines.append(",".join(str(exp[h]) for h in headers))
            csv_data = "\n".join(csv_lines)
        
        return {
            "status": "success",
            "format": "csv",
            "data": csv_data,
            "count": len(expenses)
        }
    else:
        return {"status": "error", "message": "Unsupported format. Use 'json' or 'csv'"}

@mcp.resource("expense://categories", mime_type="application/json")
def categories() -> str:
    '''Get expense categories from JSON file.'''
    try:
        if os.path.exists(CATEGORIES_PATH):
            with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
                return f.read()
        else:
            # Create default categories file if it doesn't exist
            default_categories = {
                "categories": [
                    {"name": "Food", "subcategories": ["Groceries", "Restaurants", "Takeout", "Coffee"]},
                    {"name": "Transportation", "subcategories": ["Fuel", "Public Transit", "Taxi", "Maintenance"]},
                    {"name": "Housing", "subcategories": ["Rent", "Utilities", "Maintenance", "Furniture"]},
                    {"name": "Entertainment", "subcategories": ["Movies", "Games", "Concerts", "Hobbies"]},
                    {"name": "Shopping", "subcategories": ["Clothing", "Electronics", "Gifts", "Household"]},
                    {"name": "Health", "subcategories": ["Medical", "Pharmacy", "Fitness", "Insurance"]},
                    {"name": "Education", "subcategories": ["Books", "Courses", "Software", "Subscriptions"]},
                    {"name": "Other", "subcategories": ["Miscellaneous"]}
                ]
            }
            with open(CATEGORIES_PATH, "w", encoding="utf-8") as f:
                json.dump(default_categories, f, indent=2)
            return json.dumps(default_categories)
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run()