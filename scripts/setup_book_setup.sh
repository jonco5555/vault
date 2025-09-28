# Check if Node.js is installed
if ! command -v node &> /dev/null
then
    echo "Node.js not found. Installing via Homebrew... (brew/apt install node)"
    exit 1
else
    echo "Node.js is already installed. Version: $(node -v)"
fi

npm install -g md-to-pdf
npm install -g @mermaid-js/mermaid-cli
