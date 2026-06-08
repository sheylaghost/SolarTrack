# ☀️ SolarTrack Brasil

## 🇺🇸 English

### 📌 About the Project

SolarTrack Brasil is a solar energy monitoring platform built with FastAPI that allows users to manage photovoltaic installations, record energy production readings, and generate financial and environmental reports.

The goal of the system is to help individuals and companies track the performance of their solar systems while measuring cost savings and environmental impact.

---

### 🚀 Technologies

#### Backend

* Python 3.12
* FastAPI
* SQLAlchemy
* SQLite
* JWT Authentication
* Passlib
* Pydantic

#### Frontend

* HTML
* CSS
* JavaScript

---

### 🎯 Features

#### Users

* User registration
* JWT authentication
* User profile management
* Access control

#### Solar Installations

* Installation registration
* Installation updates
* Installation listing
* Installation deactivation

#### Energy Readings

* Daily energy production tracking
* Production history
* Date filtering
* Record deletion

#### Reports

* Total energy production
* Financial savings
* CO₂ emissions avoided
* Tree equivalence calculation
* Installation summary dashboard

---

### 🌱 Problem Solved

Many solar system owners lack an easy way to monitor energy production and measure both financial savings and environmental benefits.

SolarTrack centralizes this information into a single platform, providing clear visibility into renewable energy generation and sustainability metrics.

---

### 🔐 Security

* Password hashing
* JWT authentication
* User-based access control
* Protected endpoints

---

### ⚙️ Running the Project

#### Install Dependencies

```bash
pip install fastapi uvicorn sqlalchemy passlib[bcrypt] python-jose[cryptography] python-multipart pydantic-settings
```

#### Run the Application

```bash
python solartrack.py
```

or

```bash
uvicorn solartrack:app --reload
```

---

### 📚 API Documentation

Swagger UI:

http://localhost:8000/docs

ReDoc:

http://localhost:8000/redoc

---

### 👤 Default Administrator Account

**Username:** admin

**Password:** admin123


---

### 🔮 Future Improvements

* Interactive dashboard with charts
* PDF report export
* PostgreSQL integration
* Docker support
* Automated testing with Pytest
* Cloud deployment
* Weather API integration
* Real-time monitoring
* IoT and smart sensor integration

# ☀️ SolarTrack Brasil

## 🇧🇷 Português

### 📌 Sobre o Projeto

O SolarTrack Brasil é uma plataforma de monitoramento de energia solar desenvolvida com FastAPI que permite gerenciar instalações fotovoltaicas, registrar leituras de produção energética e gerar relatórios financeiros e ambientais.

O objetivo do sistema é ajudar usuários e empresas a acompanharem o desempenho de seus sistemas solares, visualizando a economia gerada e o impacto positivo na redução das emissões de carbono.

---

### 🚀 Tecnologias Utilizadas

#### Backend

* Python 3.12
* FastAPI
* SQLAlchemy
* SQLite
* JWT Authentication
* Passlib
* Pydantic

#### Frontend

* HTML
* CSS
* JavaScript

---

### 🎯 Funcionalidades

#### Usuários

* Cadastro de usuários
* Login com autenticação JWT
* Perfil do usuário
* Controle de permissões

#### Instalações Solares

* Cadastro de instalações
* Atualização de informações
* Consulta de instalações
* Desativação de instalações

#### Leituras de Produção

* Registro diário de geração de energia
* Histórico de produção
* Filtros por período
* Exclusão de registros

#### Relatórios

* Produção total de energia
* Economia financeira acumulada
* CO₂ evitado
* Equivalência em árvores preservadas
* Resumo geral das instalações

---

### 🌱 Problema Resolvido

Muitos proprietários de sistemas fotovoltaicos não possuem uma forma simples de acompanhar a produção de energia e seus benefícios financeiros e ambientais.

O SolarTrack centraliza essas informações em uma única plataforma, permitindo um acompanhamento eficiente da geração energética e da sustentabilidade do sistema.

---

### 🔐 Segurança

* Senhas criptografadas
* Autenticação JWT
* Controle de acesso por usuário
* Rotas protegidas

---

### ⚙️ Como Executar

#### Instalar Dependências

```bash
pip install fastapi uvicorn sqlalchemy passlib[bcrypt] python-jose[cryptography] python-multipart pydantic-settings
```

#### Executar o Projeto

```bash
python solartrack.py
```

ou

```bash
uvicorn solartrack:app --reload
```

---

### 📚 Documentação

Swagger:

http://localhost:8000/docs

ReDoc:

http://localhost:8000/redoc

---

### 👤 Usuário Administrador

**Usuário:** admin

**Senha:** admin123

---
