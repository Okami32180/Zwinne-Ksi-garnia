from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, HiddenField
from wtforms.validators import DataRequired, NumberRange, Optional, Length

class AddToCartForm(FlaskForm):
    id_ksiazki = HiddenField('ID Książki', validators=[DataRequired()])
    ilosc = IntegerField('Ilość', default=1, validators=[DataRequired(), NumberRange(min=1, max=100, message="Ilość musi być między 1 a 100.")])
    submit_add = SubmitField('Dodaj do koszyka') # Differentiating submit button name

class UpdateCartItemForm(FlaskForm):
    id_elementu_koszyka = HiddenField('ID Elementu Koszyka', validators=[DataRequired()])
    ilosc = IntegerField('Ilość', validators=[DataRequired(), NumberRange(min=1, max=100)])
    submit_update = SubmitField('Aktualizuj')

class RemoveCartItemForm(FlaskForm):
    id_elementu_koszyka = HiddenField('ID Elementu Koszyka', validators=[DataRequired()])
    submit_remove = SubmitField('Usuń')

class ApplyPromoCodeForm(FlaskForm):
    kod_promocyjny = StringField('Kod promocyjny', validators=[Optional(), Length(min=1, max=50)])
    submit_promo = SubmitField('Zastosuj kod')