#!/bin/bash

# Параметры тестирования
CONCURRENCY=100    # Количество параллельных запросов
REQUESTS=10000     # Общее количество запросов на endpoint
SLEEP_INTERVAL=2  # Задержка между запусками тестов (в секундах)
SERVER="http://192.168.0.120:8000"
REPORT_DIR="api_test_reports"

# UUID для тестирования
BOOK_UUID="f7614471-7ee9-4614-a8f3-d88ef4f330f6"
AUTHOR_UUID="3e03a24e-2b83-49ff-ace7-136ee4bf5e99"
GENRE_UUID="e6bfa49b-b7f3-490b-acc3-032d92745879"
USER_UUID="55ee934a-9416-4224-8390-63d048f0dcd4"

# Создаем директорию для отчетов, если ее нет
mkdir -p "$REPORT_DIR"

# Функция для запуска теста с сохранением отчета
run_test() {
    local endpoint=$1
    local name=$2
    local report_file="${REPORT_DIR}/report_${name}_$(date +%Y%m%d_%H%M%S).txt"
    
    echo "Запуск теста для ${endpoint}..."
    ab -k -c $CONCURRENCY -n $REQUESTS "${SERVER}${endpoint}" > "$report_file" 2>&1 &
    echo "Результаты будут сохранены в ${report_file}"
    echo $! >> "${REPORT_DIR}/test_pids.txt"  # Сохраняем PID процесса
}

# Очистка экрана и старых PID файлов
clear
> "${REPORT_DIR}/test_pids.txt"

# Запуск тестов
#run_test "/api/v1/download/book/${BOOK_UUID}/cover" "book_cover"
#sleep $SLEEP_INTERVAL

#run_test "/api/v1/download/book/${BOOK_UUID}/pdf" "book_pdf"
#sleep $SLEEP_INTERVAL

run_test "/api/v1/books/get?book_id=${BOOK_UUID}" "get_book"
sleep $SLEEP_INTERVAL

run_test "/api/v1/authors/get?author_id=${AUTHOR_UUID}&user_id=${USER_UUID}" "get_author"
sleep $SLEEP_INTERVAL

run_test "/api/v1/authors/get_all?user_id=${USER_UUID}" "get_all_authors"
sleep $SLEEP_INTERVAL

run_test "/api/v1/genres/get_all?user_id=${USER_UUID}" "get_all_genres"
sleep $SLEEP_INTERVAL

run_test "/api/v1/genres/get?genre_id=${GENRE_UUID}&user_id=${USER_UUID}" "get_genre"

# Ожидание завершения всех тестов
echo "Ожидание завершения всех тестов..."
while read pid; do
    wait "$pid"
done < "${REPORT_DIR}/test_pids.txt"

echo "Все тесты завершены. Отчеты сохранены в ${REPORT_DIR}/report_*.txt"

# Вывод статистики
echo -e "\nКраткая статистика:"
grep "Requests per second" "${REPORT_DIR}"/report_*.txt
grep "Time per request" "${REPORT_DIR}"/report_*.txt

# Удаление временного файла с PID
rm "${REPORT_DIR}/test_pids.txt"