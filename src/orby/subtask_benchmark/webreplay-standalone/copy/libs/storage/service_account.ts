// service account we use to access resources for automated test creation/execution:
// 1. read/write objects in the gs://orby-warc bucket
// 2. read/write access to the following Google Sheets
//    https://docs.google.com/spreadsheets/d/1JTk1cq7kf-4DuP_FCLJeHkTgweRtrPes2RszXOrHq9E/edit
export default {
  type: 'service_account',
  project_id: 'orby-dev',
  private_key_id: 'ac763c234ecb55280e0836adad46846a17756a22',
  private_key:
    '-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCpyo+egf6QW2Lp\n2t8b07IKHwfcMQ4dmLf4IFCXV8uiN6a+UG8Jhh4jSLu9+J7Pn2y96nACIzoBX/tZ\nEeaKAvLZHCmuvfVvPKsBsS0pms69YeR86g2CMx/fQM+g3kjQS92/BegXV/mzRSMY\ntVZBh0bibAEt7ra4lGq5bHa5OIx3TQGRmueVKdMNYfuG7MSob5y/Kmt6TaE7/Kr3\nihtu6uVXyu2Jgd17DjUER+LZb5V25JP0A6ADkmXBaMBnC3SZS8aOzLGtY/pIsaFb\nzXRsy7FxkARdf/uxhwwzBqkRKhr+JLxN/3Qs+Yqo6FAba+hDmHSZT1gLXrctfSUq\nkH8d+EatAgMBAAECggEAIjW2Zyzw8fv/u3eGcXBfVGu5JTPbELqHAp7cLgoZ9Na6\nqWjCXoxfwSMz9IxFzzZjbgZwx/V6B/HjTihtp0v9yyHCAjuy2lVCbUZZ/6J52i2B\noGt2ClArsUs5KkPvLszCYm0ZvK5UmLqq3h0XQn+zmAZD3JHWzezVbgO9DgenQZf1\n0EIoXKRAFvHG3gmmm4tDzsqdtFANrFNv6sbz0FxqA8SwVIv1u06t9AyAhJYvqqlT\n6CbDIzsNexVZi6Tvt+CYhENkqv0fq8ckXOpkr6Q/TZ0LvC3UL+BDpKHH2ziBoKJ/\nUvlaI4icW1XSpstPWgNnJsArLEiiOCsOWQvdct3WvwKBgQDYnBSKFO8GYSV4Gd9f\nuGlSCwU7ZZOM+mL4eckijJeY5M1wyTVC95AJExCvD1epErFgmbr7lUIcpscxJuUx\nUxqld+aujtD+E84d9aZlb7hbujpU7KI1pANQJpQcVrFvCkVlR5tsFbIE3em4d/6z\ncEelBYr4ShcqPUkja0KCkVtrgwKBgQDIquxIN64cYUmc+O56dqSaF/3SaZcEdToJ\nEiWeqLihAORNHyLs07qiu9LkFh3ttnNreD5chgBRg/c6zKtPnipf9KIUj4TjMue3\ntHZ1F120qJpvi6sFLIkG5Tp2X/Hk144HwC+ROrvlrwjUQCeN9k4Lgppkayev+ZxA\nj2xqP3v+DwKBgBnFL/hhlzJmGmQYh+fGc9lL8Fppsk1CeMXhD1np6htJlVuGxKxr\n8Znyx7hcFezKiYnZoFJQJqZr/STO4NOmdHQdOLepzBl+V7ZexGYrDX70P/5cjMve\n8Hn3rQVWFxQD38+13jrUtfI4SJcmx4mnoQ50A12Yyvq+gdYR677G9l5rAoGAdHcn\nnh6a8iPRCsc7+l3j2P+1tKrOGKtFHMCojvZT+jY/SzeYGKYme47RrsnbYv1y7dwj\nLaYkhys1ka36e8JLy9d7Pr2xngAMlwWpfvopy9HTmIwSnXUkrpjanpu/FFe7Ompj\n8UGKjptRX4dArddXoryRiVjb9vnDo4Dapqvj9icCgYBWfkQJzdql3G9yi6Na3JSV\nnGD4T0OgyQFHJnaYeE17KwBJSmNMjGfve1FlZrzomWSbUIckoKEwu55dalScqb2K\nt2xKSjHEnzJB5BNU7Z9OsAI+cG0snzobdKfDBNCfOf7bJ55DRIp4d3GelR37pG4b\nfv8vC43MGzb/yoyQliGUQQ==\n-----END PRIVATE KEY-----\n',
  client_email: 'orbot-replay@orby-dev.iam.gserviceaccount.com',
  client_id: '106483605008367596548',
  auth_uri: 'https://accounts.google.com/o/oauth2/auth',
  token_uri: 'https://oauth2.googleapis.com/token',
  auth_provider_x509_cert_url: 'https://www.googleapis.com/oauth2/v1/certs',
  client_x509_cert_url:
    'https://www.googleapis.com/robot/v1/metadata/x509/orbot-replay%40orby-dev.iam.gserviceaccount.com',
  universe_domain: 'googleapis.com',
};
