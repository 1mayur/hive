import argparse
import os

from dotenv import load_dotenv

from bots.ws_bot import WsBot


def main():
    """Main function to start the WebSocket bot."""
    # Load environment variables from .env file
    load_dotenv()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Start a WebSocket bot for order processing")
    parser.add_argument(
        "--url", type=str, default="0.0.0.0", help="URL to host the WebSocket server"
    )
    parser.add_argument("--port", type=int, default=8765, help="Port to host the WebSocket server")
    args = parser.parse_args()

    # Check if OpenAI API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set")
        print("Please set it in a .env file or export it in your environment")
        return

    # Create and start the bot
    print(f"Starting WebSocket bot on {args.url}:{args.port}...")
    bot = WsBot(url=args.url, port=args.port)

    try:
        bot.start()
    except Exception as e:
        print(f"Error starting the bot: {e}")


if __name__ == "__main__":
    main()
