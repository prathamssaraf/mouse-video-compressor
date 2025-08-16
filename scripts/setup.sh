#!/bin/bash

# Mouse Video Compressor Setup Script
# This script sets up the development environment for the mouse video compression system

set -e  # Exit on any error

echo "🐭 Mouse Video Compressor Setup Script"
echo "======================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    if command_exists python3; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        REQUIRED_VERSION="3.9"
        
        if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
            print_success "Python $PYTHON_VERSION found"
            return 0
        else
            print_error "Python $REQUIRED_VERSION or higher is required. Found: $PYTHON_VERSION"
            return 1
        fi
    else
        print_error "Python 3 is not installed"
        return 1
    fi
}

# Function to check Node.js version
check_node_version() {
    if command_exists node; then
        NODE_VERSION=$(node --version | cut -d'v' -f2)
        REQUIRED_VERSION="16.0.0"
        
        if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$NODE_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
            print_success "Node.js $NODE_VERSION found"
            return 0
        else
            print_error "Node.js $REQUIRED_VERSION or higher is required. Found: $NODE_VERSION"
            return 1
        fi
    else
        print_error "Node.js is not installed"
        return 1
    fi
}

# Function to install system dependencies
install_system_dependencies() {
    print_status "Installing system dependencies..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Ubuntu/Debian
        if command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y \
                ffmpeg \
                libopencv-dev \
                python3-opencv \
                python3-venv \
                python3-pip \
                nodejs \
                npm \
                redis-server \
                curl \
                git
        # CentOS/RHEL/Fedora
        elif command_exists yum; then
            sudo yum install -y \
                ffmpeg \
                opencv-devel \
                python3-opencv \
                python3-venv \
                python3-pip \
                nodejs \
                npm \
                redis \
                curl \
                git
        elif command_exists dnf; then
            sudo dnf install -y \
                ffmpeg \
                opencv-devel \
                python3-opencv \
                python3-venv \
                python3-pip \
                nodejs \
                npm \
                redis \
                curl \
                git
        else
            print_warning "Unknown Linux distribution. Please install dependencies manually."
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command_exists brew; then
            brew install ffmpeg opencv python node redis
        else
            print_error "Homebrew is required on macOS. Please install it first: https://brew.sh/"
            exit 1
        fi
    else
        print_warning "Unsupported operating system. Please install dependencies manually."
    fi
}

# Function to setup Python environment
setup_python_environment() {
    print_status "Setting up Python virtual environment..."
    
    cd backend
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    pip install -r requirements.txt
    print_success "Python dependencies installed"
    
    cd ..
}

# Function to setup Node.js environment
setup_node_environment() {
    print_status "Setting up Node.js environment..."
    
    cd frontend
    
    # Install npm dependencies
    npm install
    print_success "Node.js dependencies installed"
    
    cd ..
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p videos/raw
    mkdir -p videos/compressed
    mkdir -p logs
    mkdir -p temp
    mkdir -p uploads
    mkdir -p volumes/videos/raw
    mkdir -p volumes/videos/compressed
    mkdir -p volumes/logs
    mkdir -p volumes/temp
    mkdir -p volumes/uploads
    
    print_success "Directories created"
}

# Function to setup configuration files
setup_configuration() {
    print_status "Setting up configuration files..."
    
    # Copy environment file if it doesn't exist
    if [ ! -f ".env" ]; then
        cp .env.example .env
        print_success "Environment file created from template"
        print_warning "Please edit .env file to configure your settings"
    else
        print_warning ".env file already exists"
    fi
}

# Function to setup database (if using SQLite)
setup_database() {
    print_status "Setting up database..."
    
    # For now, we'll use in-memory storage
    # If you want to add proper database setup, add it here
    
    print_success "Database setup completed"
}

# Function to run tests
run_tests() {
    print_status "Running tests..."
    
    cd backend
    source venv/bin/activate
    
    # Run Python tests if they exist
    if [ -d "../tests" ]; then
        python -m pytest ../tests/ -v
        print_success "Python tests passed"
    else
        print_warning "No Python tests found"
    fi
    
    cd ../frontend
    
    # Run React tests
    npm test -- --watchAll=false
    print_success "React tests passed"
    
    cd ..
}

# Function to start services
start_services() {
    print_status "Starting services..."
    
    # Start Redis if not already running
    if ! pgrep -x "redis-server" > /dev/null; then
        if command_exists redis-server; then
            redis-server --daemonize yes
            print_success "Redis server started"
        else
            print_warning "Redis server not found, some features may not work"
        fi
    else
        print_success "Redis server already running"
    fi
}

# Function to check setup
verify_setup() {
    print_status "Verifying setup..."
    
    # Check backend
    cd backend
    source venv/bin/activate
    python -c "import cv2, numpy, fastapi; print('Backend dependencies OK')"
    cd ..
    
    # Check frontend
    cd frontend
    npm list react >/dev/null 2>&1 && echo "Frontend dependencies OK"
    cd ..
    
    print_success "Setup verification completed"
}

# Main setup function
main() {
    echo "Starting setup process..."
    echo ""
    
    # Check prerequisites
    print_status "Checking prerequisites..."
    
    if ! check_python_version; then
        print_error "Please install Python 3.9 or higher"
        exit 1
    fi
    
    if ! check_node_version; then
        print_error "Please install Node.js 16 or higher"
        exit 1
    fi
    
    # Ask user for installation type
    echo ""
    echo "Choose installation type:"
    echo "1) Development setup (installs all dependencies)"
    echo "2) Docker setup (requires Docker and Docker Compose)"
    echo "3) Production setup"
    echo ""
    read -p "Enter your choice (1-3): " choice
    
    case $choice in
        1)
            print_status "Setting up development environment..."
            install_system_dependencies
            create_directories
            setup_python_environment
            setup_node_environment
            setup_configuration
            setup_database
            start_services
            verify_setup
            ;;
        2)
            print_status "Setting up Docker environment..."
            if ! command_exists docker; then
                print_error "Docker is not installed. Please install Docker first."
                exit 1
            fi
            if ! command_exists docker-compose; then
                print_error "Docker Compose is not installed. Please install Docker Compose first."
                exit 1
            fi
            create_directories
            setup_configuration
            echo ""
            echo "Docker setup complete. Run the following commands to start:"
            echo "  docker-compose -f docker-compose.dev.yml up --build"
            ;;
        3)
            print_status "Setting up production environment..."
            install_system_dependencies
            create_directories
            setup_python_environment
            setup_node_environment
            setup_configuration
            setup_database
            start_services
            verify_setup
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
    
    echo ""
    print_success "🎉 Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file to configure your settings"
    echo "2. Place sample videos in videos/raw/ directory"
    echo ""
    
    if [ "$choice" = "1" ] || [ "$choice" = "3" ]; then
        echo "To start the application:"
        echo "  Backend:  cd backend && source venv/bin/activate && python app.py"
        echo "  Frontend: cd frontend && npm start"
    fi
    
    echo ""
    echo "For more information, see README.md"
}

# Run main function
main "$@"