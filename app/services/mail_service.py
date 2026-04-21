"""Email service for newsletters and notifications."""
import logging
from flask import current_app, render_template_string
from flask_mail import Message
from ..extensions import mail, db
from ..models.newsletter import Newsletter
from ..models.prediction import Prediction
from ..models.fixture import Fixture

logger = logging.getLogger(__name__)


class MailService:
    """Service for sending emails."""

    # Email templates
    NEWSLETTER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #1a1a2e; color: white; padding: 20px; text-align: center; }
        .prediction { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; }
        .confidence { color: #28a745; font-weight: bold; }
        .value-bet { background: #fff3cd; border: 1px solid #ffc107; padding: 5px 10px; border-radius: 4px; }
        .footer { text-align: center; color: #666; font-size: 12px; margin-top: 20px; }
        .unsubscribe { color: #666; text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>OddsIQ Daily Picks</h1>
            <p>{{ date }}</p>
        </div>

        <h2>Today's Top Predictions</h2>

        {% for pred in predictions %}
        <div class="prediction">
            <h3>{{ pred.fixture.home_team.name }} vs {{ pred.fixture.away_team.name }}</h3>
            <p><strong>League:</strong> {{ pred.fixture.league.name }}</p>
            <p><strong>Kickoff:</strong> {{ pred.fixture.kickoff_at }}</p>
            <p><strong>Prediction:</strong> {{ pred.predicted_outcome | title }}</p>
            <p><strong>Confidence:</strong> <span class="confidence">{{ (pred.confidence_score * 100) | round(1) }}%</span></p>
            {% if pred.is_value_bet %}
            <span class="value-bet">Value Bet!</span>
            {% endif %}
        </div>
        {% endfor %}

        <p>Visit our website for more predictions and detailed analysis.</p>

        <div class="footer">
            <p>You're receiving this because you subscribed to OddsIQ newsletter.</p>
            <p><a href="#" class="unsubscribe">Unsubscribe</a></p>
        </div>
    </div>
</body>
</html>
"""

    WELCOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #1a1a2e; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; }
        .button { background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to OddsIQ!</h1>
        </div>
        <div class="content">
            <p>Hi there,</p>
            <p>Thanks for subscribing to our newsletter! You'll receive daily predictions and value bets straight to your inbox.</p>
            <p>What you'll get:</p>
            <ul>
                <li>Top 3 predictions of the day</li>
                <li>Value bet alerts</li>
                <li>Expert analysis</li>
            </ul>
            <p>Good luck with your bets!</p>
            <p>The OddsIQ Team</p>
        </div>
    </div>
</body>
</html>
"""

    def send_email(self, to, subject, html_body, text_body=None):
        """
        Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML content
            text_body: Plain text content (optional)

        Returns:
            bool: True if sent successfully
        """
        try:
            msg = Message(
                subject=subject,
                recipients=[to],
                html=html_body,
                body=text_body or 'Please view this email in an HTML-compatible client.'
            )
            mail.send(msg)
            logger.info(f'Email sent to {to}: {subject}')
            return True
        except Exception as e:
            logger.error(f'Failed to send email to {to}: {e}')
            return False

    def send_welcome_email(self, email):
        """Send welcome email to new newsletter subscriber."""
        html = render_template_string(self.WELCOME_TEMPLATE)
        return self.send_email(
            to=email,
            subject='Welcome to OddsIQ Newsletter!',
            html_body=html
        )

    def get_top_predictions(self, limit=3):
        """Get top predictions for the newsletter."""
        from datetime import datetime, timedelta

        # Get today's predictions sorted by confidence
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        predictions = Prediction.query.join(Fixture).filter(
            Fixture.kickoff_at.between(today_start, today_end),
            Fixture.status == 'upcoming'
        ).order_by(
            Prediction.confidence_score.desc()
        ).limit(limit).all()

        return predictions

    def send_newsletter_digest(self):
        """
        Send daily newsletter digest to all active subscribers.

        Returns:
            dict: {'sent': int, 'failed': int}
        """
        from datetime import datetime

        # Get top predictions
        predictions = self.get_top_predictions(limit=3)

        if not predictions:
            logger.info('No predictions available for newsletter')
            return {'sent': 0, 'failed': 0}

        # Prepare prediction data
        predictions_data = []
        for pred in predictions:
            predictions_data.append({
                'fixture': {
                    'home_team': {'name': pred.fixture.home_team.name},
                    'away_team': {'name': pred.fixture.away_team.name},
                    'league': {'name': pred.fixture.league.name},
                    'kickoff_at': pred.fixture.kickoff_at.strftime('%H:%M')
                },
                'predicted_outcome': pred.predicted_outcome,
                'confidence_score': pred.confidence_score,
                'is_value_bet': pred.is_value_bet
            })

        # Render email
        html = render_template_string(
            self.NEWSLETTER_TEMPLATE,
            predictions=predictions_data,
            date=datetime.utcnow().strftime('%B %d, %Y')
        )

        # Get active subscribers
        subscribers = Newsletter.query.filter_by(active=True).all()

        sent = 0
        failed = 0

        for subscriber in subscribers:
            success = self.send_email(
                to=subscriber.email,
                subject=f'OddsIQ Daily Picks - {datetime.utcnow().strftime("%B %d")}',
                html_body=html
            )
            if success:
                sent += 1
            else:
                failed += 1

        logger.info(f'Newsletter digest sent: {sent} successful, {failed} failed')
        return {'sent': sent, 'failed': failed}

    def send_premium_upgrade_email(self, email, plan):
        """Send confirmation email after premium upgrade."""
        subject = 'Welcome to OddsIQ Premium!'
        html = f"""
        <html>
        <body>
            <h1>You're now a Premium Member!</h1>
            <p>Thank you for upgrading to OddsIQ Premium ({plan} plan).</p>
            <p>You now have access to:</p>
            <ul>
                <li>All predictions (unlimited)</li>
                <li>Value bet alerts</li>
                <li>Expert notes and analysis</li>
                <li>Priority support</li>
            </ul>
            <p>Enjoy your premium experience!</p>
        </body>
        </html>
        """
        return self.send_email(to=email, subject=subject, html_body=html)
