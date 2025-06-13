from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class ReviewForm(FlaskForm):
    ocena = IntegerField('Ocena (1-5)', validators=[DataRequired(), NumberRange(min=1, max=5, message="Ocena musi być liczbą od 1 do 5.")])
    komentarz = TextAreaField('Komentarz (opcjonalnie)', validators=[Optional(), Length(max=1000)])
    id_ksiazki = HiddenField(validators=[DataRequired()]) # To associate review with the book
    submit = SubmitField('Dodaj recenzję')

class SearchForm(FlaskForm):
    query = StringField('Szukaj', validators=[DataRequired(), Length(min=1, max=200)])
    submit = SubmitField('Wyszukaj')