import csv
import os
from datetime import datetime
from flask import current_app
import time
import uuid

def get_payment_log_path():
    log_file = current_app.config.get('FAKE_PAYMENT_LOG_FILE', 'instance/fake_payments.csv')
    if not os.path.isabs(log_file):
        log_file = os.path.join(current_app.root_path, '..', log_file) # Assuming relative to project root
    
    # Ensure the directory for the log file exists
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError as e:
            current_app.logger.error(f"Could not create directory for payment log {log_dir}: {e}")
            # Fallback to instance path if creation fails
            instance_log_dir = os.path.join(current_app.instance_path, 'payment_logs')
            if not os.path.exists(instance_log_dir):
                 os.makedirs(instance_log_dir, exist_ok=True)
            log_file = os.path.join(instance_log_dir, 'fake_payments.csv')

    return log_file

def log_fake_transaction(order_id, user_id, amount, status, transaction_id=None):
    """Logs a fake payment transaction to a CSV file."""
    log_file_path = get_payment_log_path()
    
    file_exists = os.path.isfile(log_file_path)
    
    try:
        with open(log_file_path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if not file_exists or os.path.getsize(log_file_path) == 0:
                writer.writerow(['Timestamp', 'TransactionID', 'OrderID', 'UserID', 'Amount', 'Currency', 'Status', 'PaymentMethod'])
            
            writer.writerow([
                datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                transaction_id or str(uuid.uuid4()),
                order_id,
                user_id,
                f"{amount:.2f}",
                'PLN', # Assuming currency
                status,
                'fake_payment_system'
            ])
    except IOError as e:
        current_app.logger.error(f"Error writing to fake payment log {log_file_path}: {e}")


def process_fake_payment(order_id, user_id, amount):
    """
    Simulates a payment process.
    Logs the transaction and returns a status.
    """
    transaction_id = f"FAKE-{order_id}-{str(uuid.uuid4())[:8]}"
    current_app.logger.info(f"Rozpoczęcie fake płatności dla zamówienia #{order_id}, kwota: {amount:.2f} PLN, Użytkownik ID: {user_id}")
    log_fake_transaction(order_id, user_id, amount, 'PENDING', transaction_id)
    
    # Simulate payment processing time
    time.sleep(current_app.config.get('FAKE_PAYMENT_DELAY_SECONDS', 2.5)) # Configurable delay
    
    # Simulate success/failure (for demo, always success)
    payment_successful = True 
    
    if payment_successful:
        status = 'SUCCESS'
        current_app.logger.info(f"Fake płatność ZAKOŃCZONA SUKCESEM dla zamówienia #{order_id}.")
        log_fake_transaction(order_id, user_id, amount, status, transaction_id)
        return {"success": True, "message": "Płatność zakończona sukcesem.", "transaction_id": transaction_id}
    else:
        status = 'FAILED'
        current_app.logger.warning(f"Fake płatność NIEUDANA dla zamówienia #{order_id}.")
        log_fake_transaction(order_id, user_id, amount, status, transaction_id)
        return {"success": False, "message": "Płatność nie powiodła się.", "transaction_id": transaction_id}

def get_fake_payment_logs(page=1, per_page=20):
    """Reads payment logs from the CSV file with pagination."""
    log_file_path = get_payment_log_path()
    logs = []
    if not os.path.exists(log_file_path):
        return [], 0 # No logs, 0 total items

    try:
        with open(log_file_path, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            all_logs = list(reader) # Read all logs
            all_logs.reverse() # Show newest first

            start_index = (page - 1) * per_page
            end_index = start_index + per_page
            paginated_logs = all_logs[start_index:end_index]
            
            return paginated_logs, len(all_logs)
            
    except IOError as e:
        current_app.logger.error(f"Error reading fake payment log: {e}")
        return [], 0
    except Exception as e: # Catch other potential errors like empty file, etc.
        current_app.logger.error(f"Unexpected error reading payment log: {e}")
        return [], 0