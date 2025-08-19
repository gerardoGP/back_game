from flask import Flask
from flask_cors import CORS
from .routes import bp

app = Flask(__name__)
# Añadimos una clave secreta para habilitar las sesiones de Flask
app.secret_key = 'super-secret-key-for-demo' # En producción, esto debería ser un valor seguro y aleatorio
CORS(app, supports_credentials=True) # supports_credentials=True es necesario para las sesiones

app.register_blueprint(bp)

if __name__ == '__main__':
    app.run(debug=True)