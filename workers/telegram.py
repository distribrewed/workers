import logging
import os

from distribrewed_core.base.worker import BaseWorker
import telepot

log = logging.getLogger(__name__)


class TelegramWorker(BaseWorker):
    def __init__(self):
        super(TelegramWorker, self).__init__()
        token = os.environ.get('TELEGRAM_TOKEN')
        self.chat_id = os.environ.get('TELEGRAM_CHAT')
        if token is None:
            log.error('Provide a bot token for telegram in env variable \'TELEGRAM_TOKEN\'')
            exit(0)
        if self.chat_id is None:
            log.error('Provide a chat id for telegram in env variable \'TELEGRAM_CHAT\'')
            exit(0)
        self.bot = telepot.Bot(token)

    def telegram_bot_info(self):
        return self.bot.getMe()

    def telegram_chat_info(self):
        self.bot.getChat(self.chat_id)

    def telegram_bot_send_message(self, message):
        self.bot.sendMessage(self.chat_id, message)

if __name__ == "__main__":
    worker = TelegramWorker()
    worker.telegram_bot_send_message('Whoop Whoop')
