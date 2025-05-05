# app.py
from flask import Flask, render_template, request
from wx_api import fetch_weather, colorize_weather, fetch_datis, fetch_airport_status

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    result = ""
    datis1 = ""
    datis2 = ""
    status1 = ""
    status2 = ""

    if request.method == 'POST':
        airport1 = request.form.get('airport1', '').strip().upper()
        airport2 = request.form.get('airport2', '').strip().upper()

        if airport1 and airport2:
            raw_data = fetch_weather(airport1, airport2)
            if raw_data:
                result = colorize_weather(raw_data)

            datis1 = fetch_datis(airport1)
            datis2 = fetch_datis(airport2)
            status1 = fetch_airport_status(airport1)
            status2 = fetch_airport_status(airport2)

    return render_template('index.html', result=result, datis1=datis1, datis2=datis2, status1=status1, status2=status2)

if __name__ == '__main__':
    app.run(debug=True)
