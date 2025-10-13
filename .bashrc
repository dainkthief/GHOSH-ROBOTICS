
# GRRFP Brahma_AI Autopath
export PATH="$PATH:/data/data/com.termux/files/usr/bin"

# Auto-launch Brahma_AI
bash .termux_brahma_autostart.sh &
alias grrf='python ~/grrf_compiled.py --duration 8 --dt 0.002'
