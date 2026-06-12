import os
import sqlite3
from flask_cors import CORS
from flask import Flask, jsonify, request, send_from_directory
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config["JWT_SECRET_KEY"] = os.getenv('JWT_SECRET')
jwt = JWTManager(app)

# pasta onde sera salvo as imagens dos stickers
PASTA_UPLOADS = 'uploads'
app.config['UPLOAD_FOLDER'] = PASTA_UPLOADS

# --- CONFIGURAÇÃO DO BANCO DE DADOS (SQLite) ---
def iniciar_banco():
    # Cria (ou abre) o arquivo "banco.db" na mesma pasta do projeto
    conexao = sqlite3.connect('banco.db')
    cursor = conexao.cursor()
    
    # Cria a tabela de stickers se ela não existir
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stickers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            caminho_imagem TEXT NOT NULL,
            pontos_custo INTEGER NOT NULL
        )
    ''')
    conexao.commit()
    conexao.close()

# Executa a função para criar o banco de dados assim que o código roda
iniciar_banco()

# rota de boas vindas
@app.route('/')
def boas_vindas():
    return "Banco de dados local pronto e sistema de uploads configurado!"

# rota de login
@app.route('/login', methods=['POST'])
def login():
    dados = request.get_json()
    usuario = dados.get('usuario')
    senha = dados.get('senha')

    usuario_correto = os.getenv('ADMIN_USER')
    senha_correta = os.getenv('ADMIN_PASS')

    if usuario == usuario_correto and senha == senha_correta:
        access_token = create_access_token(identity=usuario)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({'mensagem': 'Credenciais inválidas'}), 401

# rota de cadastrar stickers
@app.route('/stickers', methods=['POST'])
@jwt_required()
def criar_sticker():
    # pega dos dados do formulario
    nome = request.form.get('nome')
    pontos_custo = request.form.get('pontos_custo')

    # pega o arquivo de imagem enviado
    arquivo_imagem = request.files.get('imagem')

    # validação para nada ir vazio
    if not nome or not pontos_custo or not arquivo_imagem:
        return jsonify({'mensagem': 'Nome, pontos e imagem são obrigatórios!'}), 400
    
    # salva o arquivo fisico da imagem na pasta 'uploads'
    # usa o nome original do arquivo do usuario
    caminho_final_imagem = os.path.join(app.config['UPLOAD_FOLDER'], arquivo_imagem.filename)
    arquivo_imagem.save(caminho_final_imagem)

    # salva as info no bd
    conexao = sqlite3.connect('banco.db')
    cursor = conexao.cursor()
    cursor.execute('''
        INSERT INTO stickers (nome, caminho_imagem, pontos_custo)
        VALUES (?, ?, ?)
    ''', (nome, caminho_final_imagem, int(pontos_custo)))
    conexao.commit()
    conexao.close()

    return jsonify({"mensagem": "Sticker criado com sucesso comimagem real"}), 201

# rota para listar os stickers
@app.route('/stickers', methods=['GET'])
def listar_stickers():
    # conecta o bd
    conexao = sqlite3.connect('banco.db')
    cursor = conexao.cursor()

    # executa o comando sql paara buscar todos os registros da tabela
    cursor.execute('SELECT id, nome, caminho_imagem, pontos_custo FROM stickers')
    linhas = cursor.fetchall() # pega todas as linhas encontradas

    conexao.close()

    # transforma as linhas em uma lista de dicionario
    lista_stickers = []
    for linha in linhas:
        sticker = {
            "id": linha[0],
            "nome": linha[1],
            "caminho_imagem": linha[2],
            "pontos_custo": linha[3]
        }

        lista_stickers.append(sticker)

    # devolve a lista em json
    return jsonify(lista_stickers), 200

# rota para abrir a imagem no navegador
@app.route('/uploads/<filename>')
def buscar_imagem_fisica(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# rota para atualizar os dados de um sticker
@app.route('/stickers/<int:sticker_id>', methods=['PUT'])
@jwt_required()
def atualizar_sticker(sticker_id):
    # pega os novos dados enviados
    conteudo_json = request.get_json()

    if not conteudo_json:
        return jsonify({"mensagem": "Nenhum dado enviado para atualização."}), 400

    nome_novo = conteudo_json.get('nome')
    pontos_custo_novo = conteudo_json.get('pontos_custo')

    # conecta ao bd
    conexao = sqlite3.connect('banco.db')
    cursor = conexao.cursor()

    # verifica se o sticker existe no bd
    cursor.execute('SELECT * FROM stickers WHERE id = ?', (sticker_id,))
    sticker = cursor.fetchone()

    if not sticker:
        conexao.close()
        return jsonify({'mensagem': 'Sticker não encontrado para a atualização'}), 404
    
    # comando de atualização
    cursor.execute('''
        UPDATE stickers
        SET nome = ?, pontos_custo = ?
        WHERE id = ?
    ''', (nome_novo, pontos_custo_novo, sticker_id))

    conexao.commit()
    conexao.close()

    return jsonify({'mensagem': f'Sticker com ID {sticker_id} atualizado com sucesso'}), 200

# rota para deletar
@app.route('/stickers/<int:sticker_id>', methods=['DELETE'])
@jwt_required()
def deletar_sticker(sticker_id):
    conexao = sqlite3.connect('banco.db')
    cursor = conexao.cursor()

    # verifica se o sticker existe
    cursor.execute('SELECT id FROM stickers WHERE id = ?', (sticker_id,))
    sticker = cursor.fetchone()

    if not sticker:
        conexao.close()
        return jsonify({'mensagem': 'Sticker não encontrado para a exclusão'}), 404
    
    # se existe, é deletado
    cursor.execute('DELETE FROM stickers WHERE id = ?', (sticker_id,))

    conexao.commit()
    conexao.close()

    return jsonify({'mensagem': f'Sticker com ID {sticker_id} deletado com sucesso'}), 200

    







if __name__ == '__main__':
    app.run(debug=True)