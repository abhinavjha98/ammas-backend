from flask import current_app
from flask_mail import Message
from threading import Thread

def send_async_email(app, msg):
    """Send email asynchronously"""
    with app.app_context():
        try:
            mail = current_app.extensions.get('mail')
            if mail:
                mail.send(msg)
        except Exception as e:
            print(f"Error sending email: {e}")

def send_email(subject, recipients, html_body, text_body=None):
    """Send email to recipients"""
    app = current_app._get_current_object()
    msg = Message(
        subject=subject,
        recipients=recipients if isinstance(recipients, list) else [recipients],
        html=html_body,
        body=text_body
    )
    Thread(target=send_async_email, args=(app, msg)).start()

def send_order_confirmation_email(user, order):
    """Send order confirmation email"""
    subject = f"Order Confirmed - {order.order_number}"
    html_body = f"""
    <html>
        <body>
            <h2>Order Confirmed!</h2>
            <p>Hello {user.name},</p>
            <p>Your order <strong>{order.order_number}</strong> has been confirmed.</p>
            <p>Total Amount: £{order.total_amount:.2f}</p>
            <p>Status: {order.status}</p>
            <p>Thank you for choosing Ammas Food!</p>
        </body>
    </html>
    """
    send_email(subject, user.email, html_body)

def send_order_status_update_email(user, order):
    """Send order status update email"""
    subject = f"Order Update - {order.order_number}"
    html_body = f"""
    <html>
        <body>
            <h2>Order Status Update</h2>
            <p>Hello {user.name},</p>
            <p>Your order <strong>{order.order_number}</strong> status has been updated to: <strong>{order.status}</strong></p>
            <p>Thank you for choosing Ammas Food!</p>
        </body>
    </html>
    """
    send_email(subject, user.email, html_body)

def send_producer_approval_email(producer):
    """Send producer approval email"""
    subject = "Producer Account Approved"
    html_body = f"""
    <html>
        <body>
            <h2>Welcome to Ammas Food!</h2>
            <p>Hello {producer.user.name},</p>
            <p>Your producer account for <strong>{producer.kitchen_name}</strong> has been approved.</p>
            <p>You can now start adding dishes and accepting orders.</p>
            <p>Thank you for joining Ammas Food!</p>
        </body>
    </html>
    """
    send_email(subject, producer.user.email, html_body)

def send_new_order_notification_to_producer(producer, order):
    """Send new order notification to producer"""
    subject = f"New Order Received - {order.order_number}"
    html_body = f"""
    <html>
        <body>
            <h2>New Order Received!</h2>
            <p>Hello {producer.user.name},</p>
            <p>You have received a new order <strong>{order.order_number}</strong>.</p>
            <p><strong>Order Details:</strong></p>
            <ul>
                <li>Order Number: {order.order_number}</li>
                <li>Total Amount: £{order.total_amount:.2f}</li>
                <li>Items: {len(order.items)}</li>
            </ul>
            <p>Please log in to your dashboard to accept or reject this order.</p>
            <p>Thank you for being part of Ammas Food!</p>
        </body>
    </html>
    """
    send_email(subject, producer.user.email, html_body)

def send_order_rejection_email(customer, order, reason):
    """Send order rejection email to customer"""
    subject = f"Order Cancelled - {order.order_number}"
    html_body = f"""
    <html>
        <body>
            <h2>Order Cancelled</h2>
            <p>Hello {customer.name},</p>
            <p>We're sorry to inform you that your order <strong>{order.order_number}</strong> has been cancelled.</p>
            <p><strong>Reason:</strong> {reason}</p>
            <p>Your payment has been refunded automatically. It may take 3-5 business days to reflect in your account.</p>
            <p>We apologize for any inconvenience.</p>
            <p>Thank you for understanding!</p>
        </body>
    </html>
    """
    send_email(subject, customer.email, html_body)


