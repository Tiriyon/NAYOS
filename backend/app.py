from flask import Flask, request, jsonify
import psycopg2
import os
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

app = Flask(__name__)

trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create({"service.name": "flask-api-service"})
    )
)

jaeger_exporter = JaegerExporter(
    agent_host_name=os.getenv("JAEGER_AGENT_HOST", "simplest-agent.observability.svc.cluster.local"),
    agent_port=int(os.getenv("JAEGER_AGENT_PORT", 6831)),
)

span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

FlaskInstrumentor().instrument_app(app)
Psycopg2Instrumentor().instrument()

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kv_store (
            id SERIAL PRIMARY KEY,
            key TEXT NOT NULL,
            value TEXT NOT NULL
        );
    ''')
    conn.commit()
    cursor.close()
    conn.close()

init_db()

@app.route('/add', methods=['POST'])
def add_entry():
    key = request.json['key']
    value = request.json['value']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO kv_store (key, value) VALUES (%s, %s)', (key, value))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'status': 'success'}), 201

@app.route('/get_all', methods=['GET'])
def get_all():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM kv_store')
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

