const OpenAI = require('openai')
const express = require('express')
const cors = require('cors')
require('dotenv').config()

const app = express()

const openai = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
});

app.use(cors());

//POST 요청 받을 수 있게 만듬
app.use(express.json()) // for parsing application/json
app.use(express.urlencoded({ extended: true })) // for parsing application/x-www-form-urlencoded

// request 와 response 라는 인자를 줘서 콜백 함수를 만든다.
// localhost:3000 브라우저에 res.sendFile() 내부의 파일이 띄워진다.
app.get('/', function(req,res) {
    res.sendFile(__dirname + "/public/main.html")
})

// POST method route
app.post('/fortuneTell', async function (req, res) {
    let { myDateTime, userMessage, threadId } = req.body
    let todayDateTime = new Date().toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })
    const assistantId = process.env.CHAT_DOGE_ASST

    if (threadId == '') {
        const emptyThread = await openai.beta.threads.create();
        threadId = emptyThread.id;
        await openai.beta.threads.messages.create(
            threadId,
            {role: "user", content: `저의 생년월일과 태어난 시간은 ${myDateTime}입니다. 오늘은 ${todayDateTime}입니다.`}
        ); 
    }
    await openai.beta.threads.messages.create(
        threadId,
        { role: "user", content: userMessage }
    );

    let run = await openai.beta.threads.runs.create(
        threadId,
        { assistant_id: assistantId }
    );

    while (run.status != "completed") {
        run = await openai.beta.threads.runs.retrieve(
            threadId,
            run.id
        );
        //time.sleep(0.5)
        await new Promise((resolve) => setTimeout(resolve, 500));
    }

    const threadMessages = await openai.beta.threads.messages.list(threadId);
    assistantLastMsg = threadMessages.data[0].content[0].text.value

    res.json({"assistant": assistantLastMsg, "threadId": threadId});
});

// 3000 포트로 서버 오픈
app.listen(3000, function() {
    console.log("start! express server on port 3000")
})