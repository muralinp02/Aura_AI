# Aura-AI

## Overview

Aura-AI is a comprehensive cybersecurity scanning and monitoring platform designed to identify, analyze, and report on various security vulnerabilities in web applications. The platform leverages AI to provide intelligent threat detection and actionable security insights.

## Features

- **Vulnerability Scanning**: Detect SQL injections, XSS, and other common web vulnerabilities
- **Network Monitoring**: Real-time network traffic analysis and visualization
- **Security Reports**: Generate detailed security reports with remediation recommendations
- **Dashboard Analytics**: Visualize security metrics and trends
- **User Authentication**: Secure login and user management via Firebase
- **Customizable Scans**: Configure scan types (Quick, Full, Custom) based on your needs

## Tech Stack

- **Frontend**: React, TypeScript, Vite
- **UI Components**: shadcn-ui, Tailwind CSS, Lucide React icons
- **State Management**: React Context API, TanStack Query
- **Authentication**: Firebase Authentication
- **Database**: Firebase Firestore
- **Visualization**: Recharts, vis-network
- **PDF Export**: jsPDF, jsPDF-autotable


## Getting Started

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn
- A Firebase account for authentication and database services

### Installation

1. Clone the repository:
   ```sh
   git clone 
   cd Aura-AI
   ```

2. Install dependencies:
   ```sh
   npm install
   ```

3. Configure Firebase:
   - Create a `.env` file in the root directory
   - Add your Firebase configuration:
     ```
     VITE_FIREBASE_API_KEY=your_api_key
     VITE_FIREBASE_AUTH_DOMAIN=your_auth_domain
     VITE_FIREBASE_PROJECT_ID=your_project_id
     VITE_FIREBASE_STORAGE_BUCKET=your_storage_bucket
     VITE_FIREBASE_MESSAGING_SENDER_ID=your_messaging_sender_id
     VITE_FIREBASE_APP_ID=your_app_id
     ```

4. Start the development server:
   ```sh
   npm run dev
   ```

5. For the backend scanning service:
   - install FastAPI `pip install fastapi uvicorn`
   - Ensure the backend API is running on `http://localhost:8000`
   - run cd backend and `uvicorn main:app --reload --port 5000`
   - Or update the API endpoint in `src/contexts/ScanContext.tsx`

## Usage

1. **Login**: Access the application using your Firebase authentication credentials
2. **Dashboard**: View overall security metrics and recent scan results
3. **Scanner**: Configure and run security scans on target websites
4. **Reports**: Generate and export detailed security reports
5. **Network**: Visualize network connections and potential threats
6. **Monitoring**: Set up continuous monitoring for critical assets

## Development

### Available Scripts

- `npm run dev` - Start the development server
- `npm run build` - Build for production
- `npm run build:dev` - Build for development
- `npm run lint` - Run ESLint
- `npm run preview` - Preview the production build

### Project Structure

```
Aura-AI/
├── public/              # Static assets
├── src/
│   ├── components/      # Reusable UI components
│   │   ├── layout/      # Layout components
│   │   ├── reports/     # Report-related components
│   │   ├── scanner/     # Scanner-related components
│   │   └── ui/          # shadcn UI components
│   ├── contexts/        # React Context providers
│   ├── firebase/        # Firebase configuration
│   ├── lib/             # Utility functions
│   ├── pages/           # Page components
│   ├── styles/          # Global styles
│   ├── App.tsx          # Main application component
│   └── main.tsx         # Application entry point
├── .env                 # Environment variables (create this)
├── package.json         # Dependencies and scripts
└── README.md            # This file
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- shadcn-ui for the beautiful UI components
- Firebase for authentication and database services
- The React community for their amazing tools and libraries
