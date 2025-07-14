#!/bin/bash

# Конфигурация тестирования
CONCURRENCY=100               # Количество параллельных запросов
REQUESTS=10000                # Общее количество запросов на endpoint
SLEEP_INTERVAL=2             # Задержка между запусками тестов (в секундах)
SERVER="http://localhost:8000"
REPORT_DIR="api_test_reports" # Директория для хранения отчетов

# UUID для тестирования
BOOK_UUID="889f31d5-fdcf-4519-a3db-222885521c13"
AUTHOR_UUID="55ee934a-9416-4224-8390-63d048f0dcd4"
GENRE_UUID="ec195ea5-2b5e-45ed-8c91-02e0429ca497"
USER_UUID="ec195ea5-2b5e-45ed-8c91-02e0429ca497"

# Создаем директорию для отчетов, если ее нет
mkdir -p "$REPORT_DIR"

# Функция для запуска теста с сохранением отчета
run_test() {
    local endpoint=$1
    local name=$2
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="${REPORT_DIR}/report_${name}_${timestamp}.txt"
    
    echo "Запуск теста для ${endpoint}..."
    echo "Тест: $name" > "$report_file"
    echo "Endpoint: ${SERVER}${endpoint}" >> "$report_file"
    echo "Дата и время: $(date)" >> "$report_file"
    echo "Параметры: $CONCURRENCY параллельных запросов, всего $REQUESTS запросов" >> "$report_file"
    echo "----------------------------------------" >> "$report_file"
    
    # Запуск Apache Benchmark
    ab -k -c $CONCURRENCY -n $REQUESTS "${SERVER}${endpoint}" >> "$report_file" 2>&1
    
    # Проверка статуса выполнения
    if [ $? -eq 0 ]; then
        echo "Успешно завершено. Результаты в ${report_file}"
    else
        echo "Ошибка при выполнении теста для ${endpoint}"
    fi
    
    # Добавляем разделитель в отчет
    echo -e "\n\n----------------------------------------" >> "$report_file"
    echo "Дополнительная информация:" >> "$report_file"
    echo "Тест завершен в: $(date)" >> "$report_file"
}

# Функция для генерации сводного отчета
generate_summary() {
    local summary_file="${REPORT_DIR}/summary_$(date +%Y%m%d_%H%M%S).txt"
    
    echo "Сводный отчет тестирования API" > "$summary_file"
    echo "Сервер: $SERVER" >> "$summary_file"
    echo "Дата: $(date)" >> "$summary_file"
    echo "----------------------------------------" >> "$summary_file"
    echo "Всего тестов: 7" >> "$summary_file"
    echo "Параметры: $CONCURRENCY параллельных запросов, $REQUESTS запросов на тест" >> "$summary_file"
    echo -e "\nРезультаты по тестам:\n" >> "$summary_file"
    
    # Собираем ключевые метрики из всех отчетов
    for report in "${REPORT_DIR}"/report_*.txt; do
        if [ -f "$report" ]; then
            echo "Тест: $(basename $report)" >> "$summary_file"
            grep "Time taken for tests:" "$report" >> "$summary_file"
            grep "Complete requests:" "$report" >> "$summary_file"
            grep "Failed requests:" "$report" >> "$summary_file"
            grep "Requests per second:" "$report" >> "$summary_file"
            grep "Time per request.*mean)" "$report" >> "$summary_file"
            echo "----------------------------------------" >> "$summary_file"
        fi
    done
    
    echo -e "\nСводный отчет сохранен в ${summary_file}"
}

# Очистка экрана
clear

echo "Начало тестирования API..."
echo "Сервер: $SERVER"
echo "Количество запросов на endpoint: $REQUESTS"
echo "Параллельных запросов: $CONCURRENCY"
echo "----------------------------------------"

# Запуск тестов последовательно
run_test "/api/v1/download/book/${BOOK_UUID}/cover" "book_cover"
sleep $SLEEP_INTERVAL

run_test "/api/v1/download/book/${BOOK_UUID}/pdf" "book_pdf"
sleep $SLEEP_INTERVAL

run_test "/api/v1/books/get?book_id=${BOOK_UUID}" "get_book"
sleep $SLEEP_INTERVAL

run_test "/api/v1/authors/get?author_id=${AUTHOR_UUID}&user_id=${USER_UUID}" "get_author"
sleep $SLEEP_INTERVAL

run_test "/api/v1/authors/get_all?user_id=${USER_UUID}" "get_all_authors"
sleep $SLEEP_INTERVAL

run_test "/api/v1/genres/get_all?user_id=${USER_UUID}" "get_all_genres"
sleep $SLEEP_INTERVAL

run_test "/api/v1/genres/get?genre_id=${GENRE_UUID}&user_id=${USER_UUID}" "get_genre"

# Генерация сводного отчета
generate_summary

# Вывод краткой статистики
echo -e "\nТестирование завершено. Краткая статистика:"
grep "Requests per second" "${REPORT_DIR}"/report_*.txt | awk -F: '{printf "%-20s %s\n", $1, $NF}'
grep "Time per request.*mean)" "${REPORT_DIR}"/report_*.txt | awk -F: '{printf "%-20s %s\n", $1, $NF}'

echo -e "\nПодробные отчеты доступны в директории ${REPORT_DIR}/"