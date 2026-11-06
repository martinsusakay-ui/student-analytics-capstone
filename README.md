# Projetu Kapstone Analitika Estudante
**Sistema Analitika Dezempenhu Estudante: Segmentasaun no Klasifikasaun ho Pipeline Big Data Real-Time**

## 👥 Tim (Grupu 1)
- Nelson Martins da Costa
- Rosalina de Jesus Gama
- Raimunda Maria Auxiliadora Ines da Costa

## 🛠️ Teknolojia ne'ebé Uza
Python, FastAPI, PostgreSQL, Apache Kafka, Apache Spark, MongoDB, Streamlit

## 🏗️ Arkitetura Sistema
Alur: Bot → FastAPI (Railway) → PostgreSQL → Kafka Producer → Kafka Broker → Spark Streaming → MongoDB → Streamlit

## 🚀 Oinsá Atu Hala'o Projetu
1. Klona repositoriu: `git clone https://github.com/USERNAME/student-analytics-capstone.git`
2. Kopia `.env.example` ba `.env` no preenxe kredensiál sira.
3. Hala'o Docker: `docker-compose up -d`
4. Instala dependénsia: `pip install -r requirements.txt`
5. Hala'o Bot: `python bot/bot_replay.py`
6. Hala'o Kafka Producer: `python pipeline/kafka_producer.py`
7. Hala'o Spark Streaming: `spark-submit pipeline/spark_streaming.py`
8. Hala'o Dashboard: `streamlit run dashboard/app.py`

## 📊 Dataset Sampel
File `data/unb/sample_logs.csv`, `data/unb/sample_notas.csv`, `data/oulad/sample_studentInfo.csv`, no `data/oulad/sample_studentVle.csv` fornese ona hanesan sampel ki'ik (linha 100) ba teste.

## 🎥 Vídeu Demostrasaun
[Link YouTube Unlisted]

## 📝 Nota
- Dataset kompletu la inklui tanba nia tamaña boot tebes. Sampel ki'ik fornese ona ba teste.
- Sei presiza kredensiál PostgreSQL husi Railway no MongoDB lokal atu hala'o sistema.