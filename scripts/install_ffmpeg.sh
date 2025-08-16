#!/bin/bash

# FFmpeg Installation Script for Mouse Video Compressor
# This script installs FFmpeg with the necessary codecs for video compression

set -e

echo "🎬 FFmpeg Installation Script"
echo "============================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if FFmpeg is already installed
check_ffmpeg() {
    if command_exists ffmpeg && command_exists ffprobe; then
        FFMPEG_VERSION=$(ffmpeg -version | head -n1 | cut -d' ' -f3)
        print_success "FFmpeg $FFMPEG_VERSION is already installed"
        
        # Check for required codecs
        print_status "Checking for required codecs..."
        
        if ffmpeg -codecs 2>/dev/null | grep -q "libx264"; then
            print_success "H.264 codec (libx264) found"
        else
            print_warning "H.264 codec (libx264) not found"
        fi
        
        if ffmpeg -codecs 2>/dev/null | grep -q "libx265"; then
            print_success "H.265 codec (libx265) found"
        else
            print_warning "H.265 codec (libx265) not found (optional)"
        fi
        
        if ffmpeg -codecs 2>/dev/null | grep -q "aac"; then
            print_success "AAC codec found"
        else
            print_warning "AAC codec not found"
        fi
        
        return 0
    else
        print_warning "FFmpeg is not installed or not in PATH"
        return 1
    fi
}

# Function to install FFmpeg on Ubuntu/Debian
install_ubuntu_debian() {
    print_status "Installing FFmpeg on Ubuntu/Debian..."
    
    # Update package list
    sudo apt-get update
    
    # Install FFmpeg with common codecs
    sudo apt-get install -y \
        ffmpeg \
        libavcodec-extra \
        libavformat-dev \
        libavutil-dev \
        libswscale-dev \
        libavresample-dev \
        pkg-config
    
    print_success "FFmpeg installed successfully"
}

# Function to install FFmpeg on CentOS/RHEL/Fedora
install_centos_rhel_fedora() {
    print_status "Installing FFmpeg on CentOS/RHEL/Fedora..."
    
    # Enable RPM Fusion repository for FFmpeg
    if command_exists dnf; then
        # Fedora
        sudo dnf install -y \
            https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm \
            https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
        
        sudo dnf install -y \
            ffmpeg \
            ffmpeg-devel
    else
        # CentOS/RHEL
        sudo yum install -y epel-release
        sudo yum localinstall -y --nogpgcheck \
            https://download1.rpmfusion.org/free/el/rpmfusion-free-release-7.noarch.rpm \
            https://download1.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-7.noarch.rpm
        
        sudo yum install -y \
            ffmpeg \
            ffmpeg-devel
    fi
    
    print_success "FFmpeg installed successfully"
}

# Function to install FFmpeg on macOS
install_macos() {
    print_status "Installing FFmpeg on macOS..."
    
    if command_exists brew; then
        # Install FFmpeg with additional codecs
        brew install ffmpeg
        print_success "FFmpeg installed successfully"
    else
        print_error "Homebrew is required for macOS installation"
        echo "Please install Homebrew first: https://brew.sh/"
        echo "Then run: brew install ffmpeg"
        return 1
    fi
}

# Function to compile FFmpeg from source (advanced)
compile_from_source() {
    print_status "Compiling FFmpeg from source..."
    print_warning "This may take 30-60 minutes depending on your system"
    
    # Create build directory
    mkdir -p ~/ffmpeg-build
    cd ~/ffmpeg-build
    
    # Download and compile dependencies
    print_status "Installing build dependencies..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update
        sudo apt-get install -y \
            autoconf \
            automake \
            build-essential \
            cmake \
            git-core \
            libass-dev \
            libfreetype6-dev \
            libgnutls28-dev \
            libmp3lame-dev \
            libsdl2-dev \
            libtool \
            libva-dev \
            libvdpau-dev \
            libvorbis-dev \
            libxcb1-dev \
            libxcb-shm0-dev \
            libxcb-xfixes0-dev \
            meson \
            ninja-build \
            pkg-config \
            texinfo \
            wget \
            yasm \
            zlib1g-dev
    fi
    
    # Compile NASM (assembler)
    print_status "Compiling NASM..."
    wget https://www.nasm.us/pub/nasm/releasebuilds/2.15.05/nasm-2.15.05.tar.bz2
    tar xjvf nasm-2.15.05.tar.bz2
    cd nasm-2.15.05
    ./autogen.sh
    ./configure --prefix="$HOME/ffmpeg-build" --bindir="$HOME/bin"
    make -j$(nproc)
    make install
    cd ..
    
    # Compile libx264
    print_status "Compiling libx264..."
    git -C x264 pull 2>/dev/null || git clone --depth 1 https://code.videolan.org/videolan/x264.git
    cd x264
    PATH="$HOME/bin:$PATH" ./configure --prefix="$HOME/ffmpeg-build" --bindir="$HOME/bin" --enable-static --enable-pic
    PATH="$HOME/bin:$PATH" make -j$(nproc)
    make install
    cd ..
    
    # Compile libx265
    print_status "Compiling libx265..."
    wget -O x265.tar.bz2 https://bitbucket.org/multicoreware/x265_git/get/master.tar.bz2
    tar xjvf x265.tar.bz2
    cd multicoreware-x265_git-*/build/linux
    PATH="$HOME/bin:$PATH" cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="$HOME/ffmpeg-build" -DENABLE_SHARED=off ../../source
    PATH="$HOME/bin:$PATH" make -j$(nproc)
    make install
    cd ../../..
    
    # Compile FFmpeg
    print_status "Compiling FFmpeg..."
    wget -O ffmpeg-snapshot.tar.bz2 https://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2
    tar xjvf ffmpeg-snapshot.tar.bz2
    cd ffmpeg
    PATH="$HOME/bin:$PATH" PKG_CONFIG_PATH="$HOME/ffmpeg-build/lib/pkgconfig" ./configure \
        --prefix="$HOME/ffmpeg-build" \
        --pkg-config-flags="--static" \
        --extra-cflags="-I$HOME/ffmpeg-build/include" \
        --extra-ldflags="-L$HOME/ffmpeg-build/lib" \
        --extra-libs="-lpthread -lm" \
        --ld="g++" \
        --bindir="$HOME/bin" \
        --enable-gpl \
        --enable-gnutls \
        --enable-libass \
        --enable-libfreetype \
        --enable-libmp3lame \
        --enable-libvorbis \
        --enable-libx264 \
        --enable-libx265 \
        --enable-nonfree
    
    PATH="$HOME/bin:$PATH" make -j$(nproc)
    make install
    hash -r
    
    cd ~
    rm -rf ~/ffmpeg-build
    
    print_success "FFmpeg compiled and installed successfully"
    print_status "FFmpeg binaries are in ~/bin/ - add this to your PATH"
}

# Function to test FFmpeg installation
test_ffmpeg() {
    print_status "Testing FFmpeg installation..."
    
    # Test basic functionality
    if ffmpeg -version >/dev/null 2>&1; then
        print_success "FFmpeg is working"
    else
        print_error "FFmpeg test failed"
        return 1
    fi
    
    # Test encoding capability
    print_status "Testing H.264 encoding..."
    
    # Create a test video (1 second, solid color)
    if ffmpeg -f lavfi -i testsrc=duration=1:size=320x240:rate=1 -c:v libx264 -preset ultrafast -f null - >/dev/null 2>&1; then
        print_success "H.264 encoding test passed"
    else
        print_error "H.264 encoding test failed"
        return 1
    fi
    
    print_success "FFmpeg installation test completed successfully"
}

# Main installation function
main() {
    echo "FFmpeg Installation for Mouse Video Compressor"
    echo ""
    
    # Check if FFmpeg is already installed
    if check_ffmpeg; then
        echo ""
        read -p "FFmpeg is already installed. Would you like to reinstall? (y/N): " reinstall
        if [[ ! $reinstall =~ ^[Yy]$ ]]; then
            print_status "Keeping existing FFmpeg installation"
            test_ffmpeg
            exit 0
        fi
    fi
    
    # Detect operating system and install accordingly
    echo ""
    echo "Choose installation method:"
    echo "1) Automatic installation (recommended)"
    echo "2) Compile from source (advanced, better performance)"
    echo ""
    read -p "Enter your choice (1-2): " choice
    
    case $choice in
        1)
            if [[ "$OSTYPE" == "linux-gnu"* ]]; then
                if command_exists apt-get; then
                    install_ubuntu_debian
                elif command_exists yum || command_exists dnf; then
                    install_centos_rhel_fedora
                else
                    print_error "Unsupported Linux distribution"
                    print_status "Please install FFmpeg manually or choose option 2"
                    exit 1
                fi
            elif [[ "$OSTYPE" == "darwin"* ]]; then
                install_macos
            else
                print_error "Unsupported operating system"
                print_status "Please install FFmpeg manually or choose option 2"
                exit 1
            fi
            ;;
        2)
            compile_from_source
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
    
    # Test the installation
    echo ""
    test_ffmpeg
    
    echo ""
    print_success "🎉 FFmpeg installation completed successfully!"
    echo ""
    echo "You can now use the Mouse Video Compressor application."
    echo "FFmpeg version:"
    ffmpeg -version | head -n1
}

# Run main function
main "$@"