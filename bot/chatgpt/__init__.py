from enum import Enum
import openai
import tiktoken


class Role(Enum):
    system = "system"
    user = "user"
    assistant = "assistant"


class Message:
    """
    メッセージのクラス
    メッセージごとにロールと内容とトークンを保持する
    """

    def __init__(self, role: Role, content: str, token: int = 0):
        self.role: Role = role
        self.content: str = content
        self.calc_token()

    def msg2dict(self) -> dict:
        return {"role": self.role.name, "content": self.content}

    def set_token(self, token: int) -> None:
        self.token = token

    def msg2str(self) -> str:
        return f"{self.role.name} : {self.content}"

    def __str__(self) -> str:
        return self.msg2str()

    def calc_token(self):
        """Returns the number of tokens used by a list of messages."""
        try:
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo-0301")
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")

        self.token = len(encoding.encode(self.content))


class Response:
    """
    レスポンスのクラス
    必要な情報を雑にまとめる
    """

    def __init__(self, response: dict):
        self.choices: dict = response.get("choices", None)
        if self.choices:
            self.messages: list[Message] = [Message(Role(
                choice["message"]["role"]), choice["message"]["content"])for choice in self.choices]
        self.created: int | None = response.get("created", None)
        self.id: str | None = response.get("id", None)
        self.model: str | None = response.get("model", None)
        self.completeion_tokens: int | None = response["usage"].get(
            "completion_tokens", None)
        self.prompt_tokens: int | None = response["usage"].get(
            "prompt_tokens", None)
        """
        print(self.choices)
        print(self.messages)
        print(self.created)
        print(self.id)
        print(self.model)
        print(self.completeion_tokens)
        print(self.prompt_tokens)
        """


class Chat:
    """
    チャットのクラス
    """

    def __init__(self, API_TOKEN: str, organization: str | None = None, model: str = "gpt-3.5-turbo", TOKEN_LIMIT: int = 4096, n: int = 1, thin_out_flag: bool = False) -> None:
        self.organization: str | None = organization
        self.history: list[Message] = []
        self.model: str = model
        self.TOKEN_LIMIT: int = TOKEN_LIMIT
        self.n: int = n
        self.thin_out_flag: bool = thin_out_flag
        self.API_TOKEN: str = API_TOKEN

    def add(self, message: list[Message] | Message, role: Role = Role.user, output: bool = False) -> None:
        """
        トークログの末尾にメッセージを追加
        """

        if type(message) is str:
            message = Message(role, message)
            self.history.append(message)
            if output:
                print(message)
        elif type(message) is list:
            if output:
                for msg in message:
                    print(msg)
            self.history.extend(message)
        elif type(message) is Message:
            self.history.append(message)
            if output:
                print(message)
        else:
            raise Exception("can't add anything that is not a message")

    def completion(self, output: bool = False) -> Message:
        """
        現在の履歴の状態で返信を得る
        戻り値はMessaegクラス
        """
        response = self.create()
        completion_token = response.completeion_tokens
        reply: Message = response.messages[0]
        reply.set_token(completion_token)
        self.history.append(reply)
        if output:
            print(reply)
        return reply

    def send(self, message: str | Message, role: Role = Role.user, output: bool = False) -> Message:
        """
        メッセージを追加して送信して返信を得る
        messageがMessageクラスならそのまま、strならMessageクラスに変換して送信
        add+completionみたいな感じ
        戻り値hはMessageクラス
        """
        if type(message) is str:
            message = Message(role, message)

        if self.get_now_token() + len(message.content) > self.TOKEN_LIMIT:
            # トークン超過しそうなら良い感じに間引くかエラーを吐く
            if self.thin_out_flag:
                self.thin_out()
            else:
                raise Exception("token overflow")

        self.add(message, output=output)
        reply = self.completion(output=output)
        self.history.append(reply)
        return reply

    def make_log(self) -> list[dict]:
        """
        メッセージインスタンスのリストをAPIに送信する形式に変換
        """
        return [hist.msg2dict() for hist in self.history]

    def get_now_token(self) -> int:
        """
        現在のトークン数を取得
        """
        return sum([x.token for x in self.history])

    def thin_out(self, n: int | None = None) -> None:
        """
        トークログをTOKEN_LIMITに基づいて8割残すように先頭から消す
        引数nで減らす分のトークン数を指定
        """
        if not n:
            limit = self.TOKEN_LIMIT * 0.8
        else:
            limit = self.TOKEN_LIMIT - n
        now_token = self.get_now_token()
        remove_token = 0
        remove_index = 0
        while now_token - remove_token > limit:
            remove_token += self.history[remove_index].token
            remove_index += 1
        self.history = self.history[remove_index:]

    def create(self) -> Response:
        """
        openaiのAPIを叩く
        """
        openai.api_key = self.API_TOKEN
        if self.organization:
            openai.organization = self.organization
        log = self.make_log()
        # print(log)
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=log,
            n=self.n
        )
        return Response(response)

    def get_history(self) -> str:
        """
        会話ログをテキスト化
        """
        text: str = ""

        for i, msg in enumerate(self.history):
            text += f"{i:03}:{msg.msg2str()[:-20]}\n"

        return text

    def remove(self, index: int) -> None:
        """
        ログの一部削除
        """
        if not 0 <= index < len(self.history):
            raise Exception("index out of range")
        self.history.remove(index)

    def reset(self):
        """
        ログの全削除
        """
        self.history = []
