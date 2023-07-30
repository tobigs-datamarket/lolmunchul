# LOLMUNCHUL
### 롤 게임 내의 한타 정보와 행동 교정 지표를 분석해 제공합니다.

안녕하세요 투빅스 제 16회 컨퍼런스 데이터 분석 프로젝트 롤문철의 레포지토리입니다. 

<img src="https://github.com/HeekyungKim6424/lolmoonchul/assets/71302565/7749fa84-d60d-42b5-a152-16af47ae112b"  width="400">

#### 롤문철이란?
교통사고 과실 컨텐츠를 다루는 [한문철TV]에서 파생
-한타 중 각 팀원의 과실 판단을 하기 위한 분석 서비스로 기존 게임 분석 서비스의 한계 해결을 목적으로 함.
1. 세부 지표 설정
2. 인자분석
3. DICE 알고리즘을 이용하여 해결

##### 한타란?

각 라인에 있던 플레이어들이 한 지점에 모여 싸우는 지점

한타가 게임의 승/패에 중요한 영향을 미치는 시점이라는 가정하에 진행한다.
→ 특정 시간 내 플레이어 간의 거리와 킬 수를 확인하여 한타 시점을 뽑아낸다. 그 후, 15-20분 사이의 한타만을 선별한다.

#### DICE모델이란?(Diverse Counterfactual Explanations for Machine Learning)

-Microsoft에서 출시한, '반사실적 설명'을 제공하는 라이브러리로, Binary Classification 문제 뿐만 아니라, Multi 및 regression에서도 지원.
-반사실적 설명이란?
기본적으로 'x'가 발생하지 않았다면 'y'가 발생하지 않았을 것으로 설명 
ML/DL에서는, 반사실적 설명이 개별 인스턴스의 '예측'(Tree 기반 XGBoostClassifier 사용)에 대한 설명으로 사용됨. 
기존 인스턴스의 '예측' 클래스를 변경하는 변수의 변화를 측정 및 설명하는 방식.
→ 적용하자면, 해당 한타에서 패배한 팀의 팀원들의 지표를 변경해가며 승리로 'y'값이 바뀔 때의 변경된 지표를 제시합니다.(GA :유전자 알고리즘 사용)

### DICE 모델 절차
Step1. Tree, MLP, Linear Regression 등 여러 모형을 학습시켜야 함. 
Step2. Dice 객체 선언
Step3. Test데이터는 한 줄씩 들어가야함.(이때, 데이터에는 우리 팀원의 지표와 상대편의 지표를 축적, 반사실적 설명을 구축하는 데에 있어 바꿔야 할 지표는 우리팀의 지표를 기준으로 함.)
→ 이 때, 우리 팀원들의 챔피언 특성(탱커,서폿,딜러)에 따라 바꿔줘야 하는 feature을 다르게 설정해주기 위해 generate_features_to_vary 함수 생성
Step4. 반사실적 설명 결과 생성

### DICE 모델 구조 (참고)
<img src="https://github.com/HeekyungKim6424/lolmoonchul/assets/71302565/ad6763f0-7349-451d-aa90-ea2a62110362"  width="300">

-https://pypi.org/project/dice/

-https://interpret.ml/DiCE/

-Dacon[신한AI, 보다 나은 금융 생활을 위한 AI 서비스 아이디어 경진대회 ] : (https://dacon.io/competitions/official/236088/codeshare/8306)

### LEAGUE OF LEGEND API
https://developer.riotgames.com/apis

### LOLMUNCHUL 관련 자료
- LOLMUNCHUL과 관련된 자세한 사항은 컨퍼런스 자료를 확인해주세요!
- [Slide](https://drive.google.com/file/d/1CbVwDC0LjWUjzKiV85uXZxSHtH8QxKH9/view?usp=sharing)

### Contributors
<table>
  <tr>
    <td align="center"><a href="https://github.com/kimheekyung6424"><img src="https://github.com/HeekyungKim6424/lolmoonchul/assets/71302565/fc49b033-062a-4807-adb2-e00508286698" width="175" height="200"><br /><sub><b>Yujin Son</b></sub></td>
    <td align="center"><a href="https://github.com/HeekyungKim6424"><img src="https://github.com/HeekyungKim6424/lolmoonchul/assets/71302565/133e92c3-49d3-4415-8383-817512ec7e68" width="200" height="200"><br /><sub><b>
    HeeKyung Kim</b></sub></td>
    <td align="center"><a href="https://github.com/ms9648"><img src="https://github.com/HeekyungKim6424/lolmoonchul/assets/71302565/afd7c6eb-ab79-4395-9c27-ff2cfebe1d10" width="200" height="200"><br /><sub><b>Minseo Kim</b></sub></td>
  </tr>
  <tr>
    <td align="center"><sub><b>투빅스 18기 </b></sub></td>
    <td align="center"><sub><b>투빅스 18기</b></sub></td>
    <td align="center"><sub><b>투빅스 19기</b></sub></td>
  </tr>
</table>
<table>
  <tr align = "center">
    <td align="center"><a href="https://github.com/DongWooLeee"><img src="https://github.com/HeekyungKim6424/lolmoonchul/assets/71302565/ee8343e5-bb10-4ab6-89c4-d4784ca55f4e" width="175" height="200"><br /><sub><b>Dongwoo Lee</b></sub></td>
    <td align="center"><a href="https://github.com/yjodev"><img src="https://github.com/HeekyungKim6424/lolmoonchul/assets/71302565/f68274e0-d783-4fdc-9924-5c22c36f5ef6" width="200" height="200"><br /><sub><b>
    Yujin Oh</b></sub></td>
  </tr>
  <tr>
    <td align="center"><sub><b>투빅스 19기</b></sub></td>
    <td align="center"><sub><b>투빅스 19기</b></sub></td>
  
</table>
