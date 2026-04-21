"""Head-to-head record model."""
from datetime import datetime
from ..extensions import db


class H2HRecord(db.Model):
    """Head-to-head record model for tracking historical matchups."""

    __tablename__ = 'h2h_records'

    id = db.Column(db.Integer, primary_key=True)
    team1_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, index=True)
    team2_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, index=True)
    match_date = db.Column(db.Date, nullable=False, index=True)
    result_for_team1 = db.Column(db.Enum('W', 'D', 'L', name='h2h_result'), nullable=False)

    # Relationships
    team1 = db.relationship('Team', foreign_keys=[team1_id], backref='h2h_as_team1')
    team2 = db.relationship('Team', foreign_keys=[team2_id], backref='h2h_as_team2')

    def to_dict(self):
        """Serialize H2H record to dictionary."""
        return {
            'id': self.id,
            'team1_id': self.team1_id,
            'team2_id': self.team2_id,
            'match_date': self.match_date.isoformat(),
            'result_for_team1': self.result_for_team1
        }

    @staticmethod
    def get_h2h_records(team1_id, team2_id, limit=5):
        """Get H2H records between two teams."""
        return H2HRecord.query.filter(
            db.or_(
                db.and_(H2HRecord.team1_id == team1_id, H2HRecord.team2_id == team2_id),
                db.and_(H2HRecord.team1_id == team2_id, H2HRecord.team2_id == team1_id)
            )
        ).order_by(db.desc(H2HRecord.match_date)).limit(limit).all()

    @staticmethod
    def calculate_h2h_score(records, perspective_team_id):
        """
        Calculate H2H score from perspective of a specific team.
        W=3pts, D=1pt, L=0pts
        Returns score normalized to 0-1 range.
        """
        if not records:
            return 0.5  # Neutral score when no H2H data

        points_map = {'W': 3, 'D': 1, 'L': 0}
        total_points = 0

        for record in records:
            if record.team1_id == perspective_team_id:
                # Result is already from this team's perspective
                total_points += points_map.get(record.result_for_team1, 0)
            else:
                # Need to flip the result
                result = record.result_for_team1
                if result == 'W':
                    total_points += points_map['L']
                elif result == 'L':
                    total_points += points_map['W']
                else:
                    total_points += points_map['D']

        max_points = len(records) * 3
        return total_points / max_points if max_points > 0 else 0.5

    def __repr__(self):
        return f'<H2HRecord team1={self.team1_id} vs team2={self.team2_id}>'
