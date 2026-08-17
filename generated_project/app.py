from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from models import User, WeatherForecast
from flask_sse import sse
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    # Add login form and authentication logic here
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/index')
@login_required
def index():
    return render_template('index.html')

@app.route('/forecast')
@login_required
def forecast():
    return render_template('forecast.html')

def update_forecast():
    while True:
        # Fetch latest forecast data from API or database
        forecast_data = WeatherForecast.query.all()
        # Broadcast updates to connected clients
        with app.app_context():
            sse.publish({'forecast': [f.to_dict() for f in forecast_data]}, type='forecast')
        time.sleep(60)  # Update every 60 seconds

def broadcast_updates():
    threading.Thread(target=update_forecast).start()

@app.route('/stream')
@login_required
def stream():
    return Response(sse.generate(), mimetype='text/event-stream')

broadcast_updates()
