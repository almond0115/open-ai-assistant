## 초기 코드 배포 후 발생한 문제

### JSON 파싱 문제 발생

```
JSON Parsing Failed: Expecting value: line 1206 column 1 (char 1807)
```

GPT에서 JSON 데이터가 날아와야 하는데 시간 지연이 길게 발생하면서 빈 공백이 떨어지는 경우가 발생했습니다. <br> 이 경우 JSON Parse 가 안되어 오류가 발생하였습니다. 

&rarr; 시도 횟수 늘리기 방안 적용

### 시간 밀림 문제 발생 (UTC 문제)

DB를 Create 할 때부터 Default로 현재 시간 타임 스탬프를 찍어놓은게 문제였습니다. 

&rarr; decision 정보를 insert할 때 local time 으로 타임 스탬프를 지정


