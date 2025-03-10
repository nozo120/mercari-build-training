FROM python:3.12-alpine
WORKDIR /app
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt 
COPY . . 
RUN addgroup --system mercari && adduser --system --ingroup mercari trainee
RUN chown -R trainee:mercari /app/db
RUN chown -R trainee:mercari /app/images

USER trainee
EXPOSE 9000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
