"""Form record model for team form tracking."""
from datetime import datetime
from ..extensions import db


class FormRecord(db.Model):
    """Form record model for tracking team performance."""

    __tablename__ = 'form_records'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, index=True)
    match_date = db.Column(db.Date, nullable=False, index=True)
    result = db.Column(db.Enum('W', 'D', 'L', name='match_result'), nullable=False)
    goals_scored = db.Column(db.Integer, default=0, nullable=False)
    goals_conceded = db.Column(db.Integer, default=0, nullable=False)

    def to_dict(self):
        """Serialize form record to dictionary."""
        return {
            'id': self.id,
            'team_id': self.team_id,
            'match_date': self.match_date.isoformat(),
            'result': self.result,
            'goals_scored': self.goals_scored,
            'goals_conceded': self.goals_conceded
        }

    @staticmethod
    def calculate_form_score(form_records):
        """
        Calculate normalized form score from form records.
        W=3pts, D=1pt, L=0pts
        Returns score normalized to 0-1 range.
        """
        if not form_records:
            return 0.5  # Neutral score when no data

        points_map = {'W': 3, 'D': 1, 'L': 0}
        total_points = sum(points_map.get(record.result, 0) for record in form_records)
        max_points = len(form_records) * 3

        return total_points / max_points if max_points > 0 else 0.5

    def __repr__(self):
        return f'<FormRecord team_id={self.team_id} date={self.match_date} result={self.result}>'
