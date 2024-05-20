FROM python:3.11

RUN apt-get update && apt-get install -y build-essential libpq-dev

WORKDIR /bot

COPY bot.py requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]