import json, uuid, openai, re
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from .models import Historico_Conversa, Historico_Conversa_Transferida
from django.utils import timezone
openai.api_key = ''

def index(request):
    if 'user_id' not in request.session:
        request.session['user_id'] = str(uuid.uuid4())
    user_id = request.session['user_id']
    historico_salvo = Historico_Conversa.objects.filter(user_id=user_id).order_by('timestamp')
    
    if 'chat_historico' not in request.session:
        request.session['chat_historico'] = [
            {"role": "system", "content": "Você é um especialista em psicopatologia. Responda de forma útil e apropriada com base no contexto de psicopatologia."
            "Ao gerar respostas, use terminologia baseada no DSM-5 ou CID-11. Considere diferentes abordagens terapêuticas (psicodinâmica, comportamental, humanista, entre outras)." 
            "Se a mensagem do usuário estiver fora desse contexto, explique educadamente que só pode ajudar em questões relacionadas a psicopatologia."}
        ]
    
    for entry in historico_salvo:
        request.session['chat_historico'].append({"role": "user", "content": entry.message})
        request.session['chat_historico'].append({"role": "assistant", "content": entry.response})
    
    request.session.modified = True
    context = {
        'user_id': user_id,
    }
    return render(request, 'ferramentaweb/index.html', context)

def gerar_caso_stream(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_input = data.get('user_input', '').strip()

            if 'chat_historico' not in request.session:
                return StreamingHttpResponse(
                    json.dumps({'error': 'Histórico de conversa não inicializado. Por favor, recarregue a página.'}),
                    content_type='application/json'
                )

            chat_historico = request.session['chat_historico']
            personalizacao = request.session.get('personalizacao', {})
            nivel_complexidade = personalizacao.get('nivel_complexidade', None)

            if nivel_complexidade and personalizacao:
                chat_historico.append({
                    "role": "system",
                    "content": (f"O usuário tem {personalizacao['idade']} anos, sexo {personalizacao['sexo']},"
                                f" histórico médico: {personalizacao['historico_medico']},"
                                f" contexto social: {personalizacao['contexto_social']}."
                                f" O nível de complexidade selecionado é {nivel_complexidade}.")
                })

            chat_historico.append({"role": "user", "content": user_input})


            if len(chat_historico) > 20:
                print("Iniciando transferência das mensagens antigas...")
                print("Tamanho do chat_historico:", len(chat_historico))
                total_mensagens = Historico_Conversa.objects.filter(user_id=request.session["user_id"]).count()
                if total_mensagens > 1:
                    mensagens_antigas = Historico_Conversa.objects.filter(user_id=request.session["user_id"]).order_by('timestamp')[:total_mensagens - 1]

                    for mensagem in mensagens_antigas:
                        Historico_Conversa_Transferida.objects.create(
                            user_id=mensagem.user_id,
                            message=mensagem.message,
                            response=mensagem.response,
                            timestamp=mensagem.timestamp,
                            nivel_complexidade=mensagem.nivel_complexidade
                        )
                        mensagem.delete()

                    print("Transferência para a tabela secundária completa.")

                request.session['chat_historico'] = request.session['chat_historico'][-2:]
                request.session.modified = True

            ultima_resposta = next(
                (msg['content'] for msg in reversed(chat_historico) if msg['role'] == 'assistant'),
                None
            )
            if ultima_resposta:
                chat_historico.append({
                    "role": "system",
                    "content": f"Continue respondendo com base no seguinte transtorno ou tema: {ultima_resposta}. Responda sempre no contexto de psicopatologia."
                })

            if len(chat_historico) == 2:
                chat_historico.insert(0, {
                    "role": "system",
                    "content": (
                        "Você é um especialista em psicopatologia. Responda apenas com base nesse contexto. Ao gerar respostas, use terminologia baseada no DSM-5 ou CID-11."
                        "Considere diferentes abordagens terapêuticas (psicodinâmica, comportamental, humanista, entre outras)."
                        "Se a pergunta não for relacionada a psicopatologia, explique educadamente que não pode ajudar com outros temas."
                    )
                })

            settings = {
                'Básico': (0.5, 500),
                'Intermediário': (0.7, 750),
                'Avançado': (0.9, 1000)
            }
            temperature, max_tokens = settings.get(nivel_complexidade, (0.7, 750))

            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=chat_historico,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            )

            def stream_response():
                accumulated_text = ''
                for chunk in response:
                    if 'choices' in chunk:
                        choice = chunk['choices'][0]
                        if 'delta' in choice and 'content' in choice['delta']:
                            content = choice['delta']['content']
                            if content:
                                accumulated_text += content
                                yield json.dumps({"response": accumulated_text}) + "\n"

                chat_historico.append({"role": "assistant", "content": accumulated_text})
                request.session.modified = True

                Historico_Conversa.objects.create(
                    user_id=request.session['user_id'],
                    message=user_input,
                    response=accumulated_text,
                    timestamp=timezone.now(),
                    nivel_complexidade=nivel_complexidade
                )

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
