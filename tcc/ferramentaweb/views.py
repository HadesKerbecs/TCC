import json, uuid, openai
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from .models import Historico_Conversa

openai.api_key = ''  # Substitua com sua chave da API

# Armazenar o histórico da conversa na sessão
def index(request):
    if 'chat_historico' not in request.session:
        request.session['chat_historico'] = [
            {"role": "system", "content": "Você é um especialista em psicopatologia. Responda de forma útil e apropriada com base no contexto de psicopatologia."}
        ]

    # Gera um ID único para o usuário, se não existir
    if 'user_id' not in request.session:
        request.session['user_id'] = str(uuid.uuid4())  # ou use um simples contador/incremento

    context = {
        'user_id': request.session['user_id'],
    }

    return render(request, 'ferramentaweb/index.html', context)

def gerar_caso_stream(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_input = data.get('user_input', '')

            # Recupera o histórico de conversa da sessão
            chat_historico = request.session.get('chat_historico', [])
            print(f"Histórico anterior: {chat_historico}")

            # Adiciona a mensagem do usuário ao histórico
            chat_historico.append({"role": "user", "content": user_input})
            print(f"Histórico atualizado: {chat_historico}")

            # Recupera a personalização da sessão, se houver
            personalizacao = request.session.get('personalizacao', {})
            if personalizacao:
                # Adiciona a personalização ao histórico de mensagens (ou em outro lugar necessário)
                nivel_complexidade = personalizacao.get('nivel_complexidade', None)
                if nivel_complexidade:
                    chat_historico.append({
                        "role": "system", 
                        "content": f"Personalização aplicada: {personalizacao}"
                    })
                else:
                    chat_historico.append({
                        "role":"system",
                        "content": f"Personalização aplicada: {personalizacao}"
                    })

            # Função de streaming para gerar a resposta
            def stream_response():
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=chat_historico,  # Envia todo o histórico da conversa, incluindo personalizações
                    max_tokens=1000,
                    temperature=0.7,
                    stream=True
                )

                accumulated_text = ''
                for chunk in response:
                    if 'choices' in chunk:
                        choice = chunk['choices'][0]
                        if 'delta' in choice and 'content' in choice['delta']:
                            content = choice['delta']['content']
                            if content:
                                accumulated_text += content
                                yield json.dumps({"response": accumulated_text}) + "\n"
                    if 'error' in chunk:
                        yield json.dumps({'error': chunk['error']['message']}) + "\n"

                # Adiciona a resposta do modelo ao histórico
                chat_historico.append({"role": "assistant", "content": accumulated_text})
                print(f"Histórico final: {chat_historico}")

                # Salva o histórico atualizado na sessão
                request.session['chat_historico'] = chat_historico
                request.session.modified = True

                yield json.dumps({"response": accumulated_text}) + "\n"

            return StreamingHttpResponse(stream_response(), content_type='application/json')
        except Exception as e:
            return StreamingHttpResponse(
                json.dumps({'error': str(e)}), 
                content_type='application/json'
            )
    else:
        return JsonResponse({'error': 'Método não permitido.'}, status=405)

def processo_user_menssagem(message):
    response = f"Você disse: {message}"
    
    return response

def processar_mensagem(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id', '').strip()
        message = request.POST.get('message', '').strip()

        if not user_id:
            return JsonResponse({'error': 'User ID é obrigatório.'}, status=400)
        if not message:
            return JsonResponse({'error': 'Mensagem é obrigatória.'}, status=400)

        # Salvar a mensagem no histórico da base de dados
        Historico_Conversa.objects.create(user_id=user_id, message=message)

        # Processar a mensagem e gerar uma resposta
        response = processo_user_menssagem(message)

        return JsonResponse({'response': response})
    else:
        return JsonResponse({'error': 'Método não permitido.'}, status=405)


def pegar_historico(request):
    user_id = request.GET.get('user_id', '')
    print(f"Recebido user_id: {user_id}")  # Adicione isto para depuração

    if not user_id:
        return JsonResponse({'error': 'ID do usuário não fornecido'}, status=400)

    # Obtemos o histórico da sessão
    chat_historico = request.session.get('chat_historico', [])
    print(f"Histórico da sessão: {chat_historico}")  # Adicione isto para depuração

    return JsonResponse(chat_historico, safe=False)

def personalizar_caso(request):
    if request.method == 'POST':
        try:
            # Verifique se o tipo de conteúdo é JSON
            if request.content_type != 'application/json':
                return JsonResponse({'error': 'Tipo de conteúdo inválido. Esperado application/json.'}, status=400)
            
            # Extrair os dados de personalização enviados pelo formulário
            data = json.loads(request.body)
            idade = data.get('idade')
            sexo = data.get('sexo')
            historico_medico = data.get('historico_medico')
            contexto_social = data.get('contexto_social')
            nivel_complexidade = data.get('nivel_complexidade')

            # Verificar se os campos obrigatórios foram enviados
            if not all([idade, sexo, historico_medico, contexto_social, nivel_complexidade]):
                return JsonResponse({'error': 'Todos os campos de personalização são obrigatórios.'}, status=400)

            # Validar dados (exemplo: idade deve ser um número)
            try:
                idade = int(idade)
            except ValueError:
                return JsonResponse({'error': 'Idade deve ser um número válido.'}, status=400)

            # Armazenar os dados de personalização na sessão
            request.session['personalizacao'] = {
                'idade': idade,
                'sexo': sexo,
                'historico_medico': historico_medico,
                'contexto_social': contexto_social,
                'nivel_complexidade': nivel_complexidade
            }

            return JsonResponse({'message': 'Personalização aplicada com sucesso.'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Falha ao decodificar o JSON enviado.'}, status=400)

    # Retornar erro se não for POST
    return JsonResponse({'error': 'Método não permitido. Use POST.'}, status=405)

def resetar_personalizacao(request):
    if request.method == 'POST':
        # Remove a personalização da sessão
        if 'personalizacao' in request.session:
            del request.session['personalizacao']
            request.session.modified = True
            return JsonResponse({'message': 'Personalização resetada com sucesso.'})
        return JsonResponse({'message': 'Nenhuma personalização encontrada para resetar.'})
    return JsonResponse({'error': 'Método não permitido.'}, status=405)

def obter_dados_personalizacao(request):
    if request.method == 'GET':
        personalizacao = request.session.get('personalizacao', {})
        return JsonResponse({'personalizacao': personalizacao})
    return JsonResponse({'error': 'Método não permitido.'}, status=405)
