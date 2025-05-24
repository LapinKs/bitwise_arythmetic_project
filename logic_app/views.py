from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.http import urlencode
import json
from .utils import generate_logic_graph, OPERATIONS
from django.template.defaulttags import register
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse, FileResponse
import os
from datetime import datetime
#generate_protocol_simplified
@register.filter
def groupby(value, arg):
    return itertools.groupby(value, lambda x: x[arg])

OP_SYMBOLS = {
    "OR": "∨", "AND": "∧", "XOR": "⊕", "EQUIV": "≡", "IMPLIES": "→",
    "NAND": "|", "NOR": "↓", "NOT_IMPLIES": "¬→", "NOT_X": "¬x", "X": "x",
    "Y": "y", "LEFT": "←", "NOT_LEFT": "¬←", "NOT_Y": "¬y"
}

@csrf_exempt
def save_attempt_log(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        log_text = data.get("log", "")
        filename = "attempt_log.txt"
        with open(filename, "a", encoding="utf-8") as f:
            f.write(log_text + "\n" + "="*80 + "\n")
        return JsonResponse({"status": "ok"})
    return JsonResponse({"error": "Invalid method"}, status=405)


# Выдача протокола модели
def download_protocol(request):
    path = "attempt_log.txt"
    if not os.path.exists(path):
        return HttpResponse("Файл не найден", status=404)

    with open(path, "rb") as f:
        response = HttpResponse(f.read(), content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="protocol.txt"'
        return response
def graph_view(request):
    # Получаем данные из GET-параметров
    fio = request.GET.get("fio", "")
    run_number = request.GET.get("run", "")
    attempts_left = int(request.GET.get("attempts", 3))
    # Десериализуем данные из JSON строк
    elements_json = request.GET.get("elements", "[]")
    level_labels_json = request.GET.get("level_labels", "[]")
    table_data_json = request.GET.get("table_data", "[]")
    max_level = request.GET.get("max_level", 0)
    try:
        elements = json.loads(elements_json)
        level_labels = json.loads(level_labels_json)
        table_data = json.loads(table_data_json)
    except json.JSONDecodeError:
        elements = []
        level_labels = []
        table_data = []

    return render(request, "logic_app/graph.html", {
        "elements": elements,
        "level_labels": level_labels,
        "table_data": table_data,
        "fio": fio,
        "run_number": run_number,
        "max_level": max_level,
        "attempts_left": attempts_left,
    })


def start_view(request):
    if request.method == "POST":
        fio = request.POST.get("fio", "").strip()
        run_number = request.POST.get("run_number", "").strip()

        errors = {}
        if not fio.replace(" ", "").isalpha():
            errors["fio"] = "ФИО должно содержать только буквы и пробелы"
        if not run_number.isdigit() or int(run_number) < 1:
            errors["run_number"] = "Номер прогона должен быть положительным числом"

        if errors:
            return render(request, "logic_app/start.html", {"errors": errors})

        # Генерируем граф
        levels = generate_logic_graph()
        elements = []
        level_labels = []
        table_data = []

        for level_idx, level in enumerate(levels):
            level_y = level_idx * 200
            level_labels.append({
                "y": level_y,
                "top_adjusted": level_y + 30,
                "label": f"Уровень {level_idx}"
            })

            for node_idx, node in enumerate(level):
                node_id = f"Y{level_idx}_{node_idx}"
                x = node_idx * 200
                y = level_y

                if level_idx == 0:
                    base, val_base, bin_val = node
                    label = f"[{val_base}]"
                    data_label = f"[{val_base}]"
                    bin_label = f"[{bin_val}]₂"
                    op = "INPUT"
                    inputs = "-"
                else:
                    op_code = node[0]
                    inputs = node[1:-3]
                    base = node[-3]
                    val_base = node[-2]
                    bin_val = node[-1]
                    symbol = OP_SYMBOLS.get(OPERATIONS[op_code], OPERATIONS[op_code])
                    label = symbol
                    data_label = f"{val_base}_{base}"
                    bin_label = f"{bin_val}"
                    for src in inputs:
                        elements.append({
                            "data": {
                                "source": f"Y{level_idx - 1}_{src}",
                                "target": node_id
                            }
                        })

                elements.append({
                    "data": {
                        "id": node_id,
                        "label": label,
                        "dataLabel": data_label,
                        "binLabel": bin_label,
                        "base": base,
                        "inputs": inputs if not isinstance(inputs, str) else []
                    },
                    "position": {"x": x, "y": y}
                })

                table_data.append({
                    "level": level_idx,
                    "node": node_idx,
                    "operation": label,
                    "inputs": inputs if isinstance(inputs, str) else ", ".join(map(str, inputs)),
                    "base": base,
                    "result": val_base,
                    "bin": bin_val
                })

        # Подготавливаем параметры для передачи
        params = {
            "fio": fio,
            "run": run_number,
            "elements": json.dumps(elements),
            "level_labels": json.dumps(level_labels),
            "table_data": json.dumps(table_data),
            "max_level":len(levels) - 1,
            "attempts": 3
        }

        # Кодируем параметры и перенаправляем
        encoded_params = urlencode(params)
        return redirect(f"{reverse('graph')}?{encoded_params}")

    return render(request, "logic_app/start.html")


def verify_view(request):
    if request.method == "POST":
        elements_json = request.POST.get("elements", "[]")
        level_labels_json = request.POST.get("level_labels", "[]")
        table_data_json = request.POST.get("table_data", "[]")
        max_level = request.POST.get("max_level", 0)
        fio = request.POST.get("fio")
        run_number = request.POST.get("run_number")
        answers = request.POST.get("answers")
        comment = request.POST.get("comment")
        attempts_left = int(request.POST.get("attempts_left", 1))
        graph_data = request.POST.get("graph_data")  # при необходимости — json.loads

        import json
        table_data = json.loads(table_data_json)
        expected_answers = [
            f"{row['result']}_{row['base']}"
            for row in table_data
            if row['level'] == max_level
        ]
        expected_str = "; ".join(expected_answers)

        # ✅ Ответы пользователя
        user_answers = [s.strip() for s in answers.split(";")]
        is_correct = len(user_answers) == len(expected_answers) and all(
            u == e for u, e in zip(user_answers, expected_answers)
        )
        return render(request, "logic_app/result.html", {
            "fio": fio,
            "run_number": run_number,
            "answers": answers,
            "comment": comment,
            "attempts_left": 4-attempts_left ,
            "elements_json":elements_json,
            "expected": expected_str,
            "level_labels_json":level_labels_json,
            "now": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "is_correct": is_correct,
            "table_data_json":table_data_json,
            "max_level":max_level
        })


def generate_report_file(request):
    # Получаем данные из сессии или контекста
    fio = request.session.get('fio', 'Неизвестный пользователь')
    run_number = request.session.get('run_number', '1')
    attempt_number = request.session.get('attempt_number', '1')
    user_answers = request.session.get('user_answers', [])
    correct_answers = request.session.get('correct_answers', [])
    comment = request.session.get('comment', 'Нет комментария')

    # Формируем текст отчета
    report_text = f"""ОТЧЁТ О ПРОВЕРКЕ МОДЕЛИ
==================================================
Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Пользователь: {fio}
Прогон №: {run_number}
Попытка: {attempt_number}

РЕЗУЛЬТАТЫ:
- Ответ пользователя: {' '.join(user_answers)}
- Правильный ответ: {' '.join(correct_answers)}

КОММЕНТАРИЙ ПОЛЬЗОВАТЕЛЯ:
{comment if comment.strip() else 'Нет комментария'}
"""

    # Создаем временный файл
    temp_file = os.path.join('temp', f'report_{fio}_{run_number}_{attempt_number}.txt')
    os.makedirs('temp', exist_ok=True)
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(report_text)

    # Возвращаем файл для скачивания
    response = FileResponse(open(temp_file, 'rb'))
    response[
        'Content-Disposition'] = f'attachment; filename="отчет_{fio}_прогон_{run_number}_попытка_{attempt_number}.txt"'
    return response


def generate_protocol_file(request):
    # Получаем данные графа из сессии
    graph_data = request.session.get('graph_data', [])
    fio = request.session.get('fio', 'Неизвестный пользователь')
    run_number = request.session.get('run_number', '1')

    # Формируем текст протокола с двумя колонками
    protocol_lines = [
        "ПРОТОКОЛ МОДЕЛИ",
        "=" * 50,
        f"Пользователь: {fio}",
        f"Прогон №: {run_number}",
        f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ""
    ]

    for level_idx, level in enumerate(graph_data):
        protocol_lines.append(f"УРОВЕНЬ {level_idx}")
        protocol_lines.append("-" * 50)

        if level_idx == 0:
            # Для входного уровня
            protocol_lines.append("Значение y | Основание k")
            protocol_lines.append("-" * 25)
            for node in level:
                protocol_lines.append(f"{node[1]} | {node[0]}")
        else:
            # Для операционных уровней
            protocol_lines.append("Операция и аргументы | Результат (основание)")
            protocol_lines.append("-" * 50)

            for node in level:
                op_code = node[0]
                inputs = node[1:-3]
                base = node[-3]
                result = node[-2]
                op_name = OPERATIONS[op_code] if op_code < len(OPERATIONS) else f"Операция {op_code}"

                # Формируем строку аргументов
                args = []
                for i in inputs:
                    prev_node = graph_data[level_idx - 1][i]
                    args.append(f"{prev_node[1]}_{prev_node[0]}")
                args_str = ", ".join(args)

                # Формируем строку операции
                operation_str = f"{op_name} ({args_str})"
                result_str = f"{result}_{base}"

                protocol_lines.append(f"{operation_str} | {result_str}")

        protocol_lines.append("=" * 50)
        protocol_lines.append("")

    # Создаем временный файл
    temp_file = os.path.join('temp', f'protocol_{fio}_{run_number}.txt')
    os.makedirs('temp', exist_ok=True)
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(protocol_lines))

    # Возвращаем файл для скачивания
    response = FileResponse(open(temp_file, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="протокол_{fio}_прогон_{run_number}.txt"'
    return response


def get_report_content(request):
    if request.method == "GET":
    # Получаем данные для отчета
        fio = request.GET.get('fio', 'Неизвестный пользователь')
        run_number = request.GET.get('run_number', '1')
        attempt_number = request.GET.get('attempt_number', '1')
        user_answers = request.GET.get('user_answers', [])
        correct_answers = request.GET.get('correct_answers', [])
        comment = request.GET.get('comment', 'Нет комментария')

        # Формируем текст отчета
        report_text = f"""ОТЧЁТ О ПРОВЕРКЕ МОДЕЛИ
    ==================================================
    Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    Пользователь: {fio}
    Прогон №: {run_number}
    Попытка: {attempt_number}
    
    РЕЗУЛЬТАТЫ:
    - Ответ пользователя: {' '.join(user_answers)}
    - Правильный ответ: {' '.join(correct_answers)}
    
    КОММЕНТАРИЙ ПОЛЬЗОВАТЕЛЯ:
    {comment if comment.strip() else 'Нет комментария'}
    """
        return JsonResponse(
            {'content': report_text, 'filename': f'отчет_{fio}_прогон_{run_number}_попытка_{attempt_number}.txt'})


def get_protocol_content(request):
    if request.method == "GET":
        # Получаем данные графа из сессии
        graph_data = request.GET.get('graph_data', [])
        fio = request.GET.get('fio', 'Неизвестный пользователь')
        run_number = request.GET.get('run_number', '1')

        # Формируем текст протокола
        protocol_lines = [
            "ПРОТОКОЛ МОДЕЛИ",
            "=" * 50,
            f"Пользователь: {fio}",
            f"Прогон №: {run_number}",
            f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]

        for level_idx, level in enumerate(graph_data):
            protocol_lines.append(f"УРОВЕНЬ {level_idx}")
            protocol_lines.append("-" * 50)

            if level_idx == 0:
                protocol_lines.append("Значение y | Основание k")
                protocol_lines.append("-" * 25)
                for node in level:
                    protocol_lines.append(f"{node[1]} | {node[0]}")
            else:
                protocol_lines.append("Операция и аргументы | Результат (основание)")
                protocol_lines.append("-" * 50)

                for node in level:
                    op_code = node[0]
                    inputs = node[1:-3]
                    base = node[-3]
                    result = node[-2]
                    op_name = OPERATIONS[op_code] if op_code < len(OPERATIONS) else f"Операция {op_code}"

                    args = [f"{graph_data[level_idx - 1][i][1]}_{graph_data[level_idx - 1][i][0]}" for i in inputs]
                    operation_str = f"{op_name} ({', '.join(args)})"
                    result_str = f"{result}_{base}"

                    protocol_lines.append(f"{operation_str} | {result_str}")

            protocol_lines.append("=" * 50)
            protocol_lines.append("")

        protocol_text = "\n".join(protocol_lines)
        return JsonResponse({'content': protocol_text, 'filename': f'протокол_{fio}_прогон_{run_number}.txt'})