# frodo-web

## Development Environment Setup

### 0. Prerequisites

Make sure these installed:
- Python >=3.12
- Frodo CLI =3.0.3
- Node.js >=20.11.0
- npm >=10.2.0
- Git >=2.30.0

### 1. Clone the repository
```bash
git clone https://github.com/aaronwang0509/frodo-web.git
```

### 2. Run the setup script
```bash
cd development
```

Edit `dev.json` and fill paths of `paic_config_bare_repo` and `paic_config_path` for local git repository:
```json
"paic_config_bare_repo": "/path/to/your/bare/repo",
"paic_config_path": "/path/to/your/working/repo",
```

Then run:
```bash
pip install packaging
python setup.py
```

### 3. Start the backend server
```bash
cd backend
source ./venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Start the frontend server
```bash
cd frontend
npm start
```

### 5. Access the app
- Backend APIs: http://localhost:8000
- Frontend: http://localhost:3000

## Development Flow

### 1. Clone the repo to local

### 2. Create a new issue on GitHub
   <img src="development/figs/fig1.jpg" alt="fig1" width="1000"/>
   
   Add a title and description for the issue, add a label and assign it to yourself.

### 3. Create a branch for this issue
   <img src="development/figs/fig2.jpg" alt="fig2" width="900"/>

   <img src="development/figs/fig3.jpg" alt="fig3" width="400"/>

### 4. Checkout the branch on local repo  
   <img src="development/figs/fig4.jpg" alt="fig4" width="450"/>

### 5. Make changes locally

### 6. Commit and push to feature branch

### 7. Open a pull request on GitHub
   <img src="development/figs/fig5.jpg" alt="fig5" width="900"/>

### 8. Let other team members review and merge to main branch
