/**
 * 김기사랩 "투자 검토 요청" 폼 백엔드 (Google Apps Script Web App)
 *
 * 설정 방법
 * 1) script.new 로 새 Apps Script 프로젝트를 만든다.
 * 2) 아래 코드 전체를 복사해서 Code.gs에 붙여넣는다.
 * 3) 구글 드라이브에 사업계획서 백업용 폴더를 하나 만들고, 폴더 URL에서 ID를 복사해
 *    아래 DRIVE_FOLDER_ID 값에 넣는다.
 *    (폴더 URL 예: https://drive.google.com/drive/folders/<이 부분이 ID>)
 * 4) 배포 > 새 배포 > 유형: 웹 앱
 *    - 실행 계정: 나
 *    - 액세스 권한: 전체 사용자(Anyone)
 *    로 설정 후 배포한다. 처음 배포 시 권한 승인 화면이 뜨면 허용한다.
 * 5) 배포 후 나오는 웹앱 URL(.../exec)을 복사해서
 *    build.py 상단의 APPS_SCRIPT_URL 값에 붙여넣고 다시 빌드한다.
 * 6) 코드를 수정하면 "배포 > 배포 관리 > 수정 > 새 버전"으로 재배포해야 반영된다.
 */

var DRIVE_FOLDER_ID = 'YOUR_DRIVE_FOLDER_ID';
var TO_EMAIL = 'IR@kimgisacompany.com';
var MAX_ATTACH_BYTES = 20 * 1024 * 1024; // 20MB (Gmail 첨부 한도 25MB 대비 여유)

function doPost(e) {
  try {
    var p = e.parameter || {};

    var company = p.company || '';
    var applicant = p.applicant || '';
    var founded = p.founded || '';
    var itemName = p.itemName || '';
    var itemSummary = p.itemSummary || '';
    var phone = p.phone || '';
    var email = p.email || '';
    var valuation = p.valuation || '';

    var driveUrl = '';
    var attachments = [];
    var file = null;

    // 브라우저에서 파일을 base64 문자열로 인코딩해 보내온다.
    // (Apps Script doPost는 <input type="file">이 실어 보낸 실제 Blob을
    //  e.parameter로 안정적으로 파싱하지 못하는 알려진 제약이 있어, 이 방식이 필요하다.)
    if (p.pitchFileData) {
      var bytes = Utilities.base64Decode(p.pitchFileData);
      file = Utilities.newBlob(bytes, p.pitchFileType || 'application/pdf', p.pitchFileName || 'pitch.pdf');
    }

    if (file && file.getBytes().length > 0) {
      var folder = DriveApp.getFolderById(DRIVE_FOLDER_ID);
      var savedName = (company || '무제') + ' - ' + file.getName();
      var driveFile = folder.createFile(file).setName(savedName);
      driveUrl = driveFile.getUrl();

      if (file.getBytes().length <= MAX_ATTACH_BYTES) {
        attachments.push(file);
      }
    }

    var subject = '[투자 검토 요청] ' + company;
    var bodyLines = [
      '회사명: ' + company,
      '신청자 성함/직함: ' + applicant,
      '법인 설립 일자: ' + founded,
      '사업 아이템명: ' + itemName,
      '사업 아이템 요약: ' + itemSummary,
      '연락처: ' + phone,
      '이메일: ' + email,
      '희망 Valuation 및 투자금액: ' + valuation
    ];

    if (driveUrl) {
      if (attachments.length > 0) {
        bodyLines.push('', '사업계획서: 메일 첨부파일 참고 (Drive 백업: ' + driveUrl + ')');
      } else {
        bodyLines.push('', '사업계획서(용량 초과로 메일 첨부 대신 링크로 전달): ' + driveUrl);
      }
    } else {
      bodyLines.push('', '사업계획서: 첨부되지 않음');
    }

    var mailOptions = {};
    if (attachments.length > 0) {
      mailOptions.attachments = attachments;
    }
    // MailApp은 '익명 공유 서버'로 발송되어 동일 계정의 전달(포워딩) 규칙과
    // 잘 맞물리지 않는 경우가 있어, 실제 계정으로 발송하는 GmailApp을 사용한다.
    GmailApp.sendEmail(TO_EMAIL, subject, bodyLines.join('\n'), mailOptions);

    return ContentService
      .createTextOutput(JSON.stringify({ ok: true }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: String(err) }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService
    .createTextOutput(JSON.stringify({ ok: true, message: 'IR form endpoint is running.' }))
    .setMimeType(ContentService.MimeType.JSON);
}
