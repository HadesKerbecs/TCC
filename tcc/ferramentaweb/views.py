import json, uuid, openai, re
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from .models import Historico_Conversa
from django.utils import timezone

openai.api_key = ''

def index(request):
    if 'chat_historico' not in request.session:
        request.session['chat_historico'] = [
            {"role": "system", "content": "Você é um especialista em psicopatologia. Responda de forma útil e apropriada com base no contexto de psicopatologia."}
        ]

    if 'user_id' not in request.session:
        request.session['user_id'] = str(uuid.uuid4())

    context = {
        'user_id': request.session['user_id'],
    }

    return render(request, 'ferramentaweb/index.html', context)

def normalizar_texto(texto):
    """Normaliza o texto removendo caracteres especiais e convertendo para minúsculas."""
    return re.sub(r'\W+', ' ', texto.lower()).strip()

def deve_continuar_conversa(user_input, chat_historico):
    user_input_normalizado = normalizar_texto(user_input)

    # Verifica se a última mensagem do assistente contém informações relacionadas
    ultima_resposta_assistente = next((msg for msg in reversed(chat_historico) if msg['role'] == 'assistant'), None)
    
    if ultima_resposta_assistente:
        ultima_resposta = normalizar_texto(ultima_resposta_assistente['content'])

        # Se a entrada do usuário mencionar alguma parte da última resposta do assistente, considera como continuidade
        if any(term in user_input_normalizado for term in ultima_resposta.split()):
            return True

    return False

def gerar_caso_stream(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_input = data.get('user_input', '').strip()

            # Inicializa ou recupera o histórico de conversas da sessão
            chat_historico = request.session.get('chat_historico', [])
            print("Histórico de conversa antes da nova entrada:", chat_historico)  # Log do histórico

            # Verifica se o usuário deseja continuar a conversa
            if deve_continuar_conversa(user_input, chat_historico):
                ultima_mensagem_assistente = next((msg for msg in reversed(chat_historico) if msg['role'] == 'assistant'), None)
                if ultima_mensagem_assistente:
                    print("Última mensagem do assistente:", ultima_mensagem_assistente['content'])  # Log da última mensagem
                    user_input = f"{user_input} Continuando com: {ultima_mensagem_assistente['content']}"

            print("Entrada do usuário para processamento:", user_input)  # Log da entrada do usuário

            # Atualiza o histórico de mensagens com a entrada do usuário
            chat_historico.append({"role": "user", "content": user_input})

            # Limite de mensagens no histórico
            if len(chat_historico) > 50:
                # Remove as 10 mensagens mais antigas
                chat_historico = chat_historico[-50:]
                print("Histórico ajustado para manter apenas as últimas 50 mensagens.")  # Log após ajuste

            # Configurações de personalização e complexidade
            personalizacao = request.session.get('personalizacao', {})
            nivel_complexidade = personalizacao.get('nivel_complexidade', None)

            if nivel_complexidade and personalizacao:
                # Adiciona informações de personalização ao histórico
                chat_historico.append({
                    "role": "system", 
                    "content": (f"O usuário tem {personalizacao['idade']} anos, sexo {personalizacao['sexo']}," 
                                f" histórico médico: {personalizacao['historico_medico']}," 
                                f" contexto social: {personalizacao['contexto_social']}." 
                                f" O nível de complexidade selecionado é {nivel_complexidade}.")
                })

            # Responde ao usuário
            def stream_response():
                settings = {
                    'Básico': (0.5, 500),
                    'Intermediário': (0.7, 750),
                    'Avançado': (0.9, 1000)
                }
                temperature, max_tokens = settings.get(nivel_complexidade, (0.7, 750))

                print("Configurando a chamada para a API:", {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "historico_mensagens": chat_historico
                })  # Log das configurações da API

                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=chat_historico,
                    max_tokens=max_tokens,
                    temperature=temperature,
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

                # Atualiza o histórico após a resposta ser gerada
                chat_historico.append({"role": "assistant", "content": accumulated_text})
                request.session['chat_historico'] = chat_historico
                request.session.modified = True

                # Salva no banco de dados
                Historico_Conversa.objects.create(
                    user_id=request.session['user_id'],
                    message=user_input,
                    response=accumulated_text,
                    timestamp=timezone.now(),
                    nivel_complexidade=nivel_complexidade
                )

                # Log da última mensagem salva
                print("Última mensagem salva:")
                print(f"Usuário: {user_input}")
                print(f"Assistente: {accumulated_text}")

                yield json.dumps({"response": accumulated_text}) + "\n"

            return StreamingHttpResponse(stream_response(), content_type='application/json')

        except Exception as e:
            print(f"Erro durante o processamento: {str(e)}")  # Log de erro
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

        print(f"Recebido user_id: {user_id}")
        print(f"Recebida mensagem: {message}")

        if not user_id:
            return JsonResponse({'error': 'User ID é obrigatório.'}, status=400)
        if not message:
            return JsonResponse({'error': 'Mensagem é obrigatória.'}, status=400)

        try:
            historico = Historico_Conversa.objects.create(user_id=user_id, message=message)
            print(f"Histórico salvo: {historico}")

            response = f"Você disse: {message}"

            return JsonResponse({'response': response})
        except Exception as e:
            print(f"Erro ao salvar no banco de dados: {e}")
            return JsonResponse({'error': 'Erro ao processar a mensagem.'}, status=500)
    else:
        return JsonResponse({'error': 'Método não permitido.'}, status=405)


def salvar_historico(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            message = data.get('message')
            response = data.get('response')

            if user_id and message and response:
                Historico_Conversa.objects.create(
                    user_id=user_id, 
                    message=message, 
                    response=response
                )
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Dados incompletos'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)

def pegar_historico(request):
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse([], safe=False)

    try:
        historico = Historico_Conversa.objects.filter(user_id=user_id).order_by('timestamp')
        
        dados_formatados = []
        for item in historico:
            formatted_entry = {
                'message': item.message.replace('\n', '<br>'),
                'response': item.response.replace('\n', '<br>'),
                'timestamp': item.timestamp.isoformat(),
                'user_id': item.user_id
            }
            dados_formatados.append(formatted_entry)

        return JsonResponse(dados_formatados, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def personalizar_caso(request):
    if request.method == 'POST':
        try:
            if request.content_type != 'application/json':
                return JsonResponse({'error': 'Tipo de conteúdo inválido. Esperado application/json.'}, status=400)
            
            data = json.loads(request.body)
            idade = data.get('idade')
            sexo = data.get('sexo')
            historico_medico = data.get('historico_medico')
            contexto_social = data.get('contexto_social')
            transtorno = data.get('transtornoClinico')
            nivel_complexidade = data.get('nivel_complexidade')

            if not all([idade, sexo, historico_medico, contexto_social, transtorno, nivel_complexidade]):
                return JsonResponse({'error': 'Todos os campos de personalização são obrigatórios.'}, status=400)

            try:
                idade = int(idade)
            except ValueError:
                return JsonResponse({'error': 'Idade deve ser um número válido.'}, status=400)

            request.session['personalizacao'] = {
                'idade': idade,
                'sexo': sexo,
                'historico_medico': historico_medico,
                'contexto_social': contexto_social,
                'transtorno': transtorno,
                'nivel_complexidade': nivel_complexidade
            }

            return JsonResponse({'message': 'Personalização aplicada com sucesso.'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Falha ao decodificar o JSON enviado.'}, status=400)

    return JsonResponse({'error': 'Método não permitido. Use POST.'}, status=405)

def resetar_personalizacao(request):
    if request.method == 'POST':
        if 'personalizacao' in request.session:
            del request.session['personalizacao']
            request.session.modified = True
            return JsonResponse({'message': 'Personalização resetada com sucesso.'})
        return JsonResponse({'message': 'Nenhuma personalização encontrada para resetar.'})
    return JsonResponse({'error': 'Método não permitido.'}, status=405)

def obter_dados_personalizacao(request):
    if request.method == 'GET':
        personalizacao = request.session.get('personalizacao', {})
        return JsonResponse(personalizacao)
    return JsonResponse({'error': 'Método não permitido.'}, status=405)