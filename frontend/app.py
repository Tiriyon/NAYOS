from flask import Flask, render_template, request, redirect, url_for
import requests
import os
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

app = Flask(__name__)

trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create({"service.name": "flask-frontend"})
    )
)

jaeger_exporter = JaegerExporter(
    agent_host_name=os.getenv("JAEGER_AGENT_HOST", "simplest-agent.observability.svc.cluster.local"),
    agent_port=int(os.getenv("JAEGER_AGENT_PORT", 6831)),
)

span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

API_URL = os.getenv("API_URL", "http://api_app.test.svc.cluster.local:5000")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        key = request.form['key']
        value = request.form['value']
        requests.post(f'{API_URL}/add', json={'key': key, 'value': value})
        return redirect(url_for('index'))

    response = requests.get(f'{API_URL}/get_all')
    entries = response.json()
    return render_template('index.html', entries=entries)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

