# AI Projects Portfolio 🤖

A curated collection of artificial intelligence and machine learning projects exploring large language models, intelligent agents, natural language processing, and automation systems.

## 📚 Projects

### 1. [Financial Document Analyzer](./financial-document-analyzer/)
**Status:** ✅ Complete | **Tech:** Python, Google Gemini AI, pdfplumber

An intelligent agent that automatically analyzes financial documents (bank statements and credit card statements) using Google's Gemini AI with function calling capabilities.

**Key Features:**
- Automated PDF text extraction
- Document classification with confidence scoring
- Structured data extraction (account details, transactions, balances)
- Natural language output formatting
- Privacy-aware processing (redacts sensitive information)

**Highlights:**
- Implements agentic workflow with function calling
- Handles multiple document types (bank statements, credit cards)
- Extracts and structures complex financial data
- Provides human-readable analysis

[View Project Details →](./financial-document-analyzer/)

---

### 2. [Healthcare Management System](./health_care_management/)
**Status:** ✅ Complete | **Tech:** Python, OpenAI GPT, AutoGen, FastAPI, MongoDB

A multi-agent AI system for healthcare management that automates patient scheduling, prescription management, and administrative tasks using autonomous AI agents.

**Key Features:**
- Multi-agent architecture with specialized roles (receptionist, doctor assistant, admin, health insights)
- Intelligent appointment booking with doctor availability optimization
- Automated prescription generation and management
- Patient health history tracking and analytics
- RESTful API with web interface
- MongoDB integration for persistent data storage

**Highlights:**
- Implements AutoGen framework for agent orchestration
- Role-based agent routing system
- Direct task execution without unnecessary confirmations
- Scalable agent-based architecture for healthcare workflows
- Real-time patient and appointment management

[View Project Details →](./health_care_management/)

---

## 🛠️ Technologies & Tools

**Languages:**
- Python 3.8+

**AI/ML Frameworks:**
- Google Gemini AI
- OpenAI GPT API
- AutoGen - Multi-agent framework
- LangChain (planned)

**Libraries & Tools:**
- pdfplumber - PDF processing
- FastAPI - API development
- MongoDB - Database storage
- Motor - Async MongoDB driver
- Pydantic - Data validation
- Streamlit - UI development (planned)
- Jupyter - Experimentation and analysis

**Development Tools:**
- Git & GitHub
- VS Code
- Docker (planned)

## 📂 Repository Structure
```
ai-projects/
│
├── financial-document-analyzer/    # Financial document analysis agent
│   ├── agent.py                    # Main agent implementation
│   ├── README.md                   # Project documentation
│   └── requirements.txt            # Project dependencies
│
├── health_care_management/         # Healthcare AI agent system
│   ├── agents.py                   # Multi-agent implementation
│   ├── db_tools.py                 # Database operations
│   ├── api.py                      # FastAPI backend
│   ├── main.py                     # Test suite
│   ├── templates/                  # Web UI templates
│   ├── requirements.txt            # Project dependencies
│   └── .gitignore                  # Project-specific ignores
│
├── shared/                         # Shared utilities and helpers
│   ├── utils.py                    # Common utility functions
│   └── config.py                   # Shared configuration
│
├── .gitignore                      # Git ignore rules
├── README.md                       # This file
└── LICENSE                         # MIT License
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git
- MongoDB (for healthcare management system)

### Installation
```bash
# Clone the repository
git clone https://github.com/SampatPolireddi/AI_Repo.git
cd ai-projects

# Navigate to a specific project
cd financial-document-analyzer

# Install project-specific dependencies
pip install -r requirements.txt
```

### Configuration

Most projects require API keys. Set them as environment variables:
```bash
# For Google Gemini projects
export GOOGLE_API_KEY="your-api-key-here"

# For OpenAI projects
export OPENAI_API_KEY="your-api-key-here"
```

Alternatively, create a `.env` file in the project directory:
```
GOOGLE_API_KEY=your-api-key-here
OPENAI_API_KEY=your-api-key-here
```

## 🎯 Project Goals

- **Explore** cutting-edge AI technologies and frameworks
- **Build** practical applications leveraging large language models
- **Experiment** with agentic workflows and autonomous systems
- **Learn** best practices in AI/ML development
- **Create** reusable components and utilities
- **Document** the learning journey and share knowledge

## 🔮 Upcoming Projects

- **Conversational AI Chatbot** - Multi-turn conversation system
- **Document Q&A System** - RAG-based question answering
- **Code Assistant** - AI-powered coding helper
- **Image Analysis Tool** - Computer vision application
- **Data Analysis Agent** - Automated data exploration

## 📖 Learning Resources

This portfolio is built using knowledge from:
- Google AI Documentation
- Anthropic Claude Documentation
- OpenAI API Guides
- LangChain Documentation
- Research papers and technical blogs
- Online courses and tutorials

## 🤝 Contributing

This is a personal learning repository, but feedback and suggestions are always welcome!

- **Found a bug?** Open an issue
- **Have a suggestion?** Start a discussion
- **Want to contribute?** Feel free to fork and submit a PR

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📧 Contact

**Sampat Polireddi**

- GitHub: [@SampatPolireddi](https://github.com/SampatPolireddi)
- Repository: [AI_Repo](https://github.com/SampatPolireddi/AI_Repo)

## ⭐ Acknowledgments

- Google Gemini AI team for the powerful language models
- The open-source AI community for tools and inspiration
- All contributors and supporters

---

<p align="center">
  <i>Building the future, one AI project at a time</i> 🚀
</p>

<p align="center">
  Made with ❤️ and Python
</p>

---

**Last Updated:** November 2025
