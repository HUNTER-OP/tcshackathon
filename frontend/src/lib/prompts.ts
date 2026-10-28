import type { Lang } from './types'

export const PROMPTS: Record<Lang, string[]> = {
  en: [
    "What's my balance?",
    'Can I afford a 5 lakh car loan?',
    'How much did I spend last month?',
    'What are the FD interest rates?',
    'Block my debit card',
    'Talk to a human',
  ],
  hi: [
    'मेरा बैलेंस कितना है?',
    'क्या मैं 5 लाख का कार लोन ले सकता हूँ?',
    'पिछले महीने मैंने खाने पर कितना खर्च किया?',
    'FD पर ब्याज दर क्या है?',
    'मेरा कार्ड खो गया, ब्लॉक करो',
    'किसी इंसान से बात करनी है',
  ],
  kn: [
    'ನನ್ನ ಬ್ಯಾಲೆನ್ಸ್ ಎಷ್ಟು?',
    'ನನಗೆ 5 ಲಕ್ಷ ಕಾರು ಸಾಲ ಸಿಗುತ್ತದೆಯೇ?',
    'ಕಳೆದ ತಿಂಗಳು ನಾನು ಎಷ್ಟು ಖರ್ಚು ಮಾಡಿದೆ?',
    'FD ಬಡ್ಡಿ ದರ ಎಷ್ಟು?',
    'ನನ್ನ ಕಾರ್ಡ್ ಬ್ಲಾಕ್ ಮಾಡಿ',
    'ಗ್ರಾಹಕ ಸೇವೆಯೊಂದಿಗೆ ಮಾತನಾಡಬೇಕು',
  ],
  hinglish: [
    'mera balance kitna hai?',
    'kya main 5 lakh ka car loan afford kar sakta hoon?',
    'pichle mahine kitna kharcha kiya?',
    'FD ka interest rate kya hai?',
    'mera card kho gaya, block karo',
    'kisi insaan se baat karni hai',
  ],
}

export const GREETING: Record<Lang, { title: string; line: string }> = {
  en: { title: 'Ask your bank anything.', line: 'Balances, spending, loans and rates, answered from your real account in English, हिन्दी, ಕನ್ನಡ or Hinglish.' },
  hi: { title: 'अपने बैंक से कुछ भी पूछिए।', line: 'बैलेंस, खर्च, लोन और ब्याज दरें, आपके असली खाते से, आपकी भाषा में।' },
  kn: { title: 'ನಿಮ್ಮ ಬ್ಯಾಂಕ್‌ಗೆ ಏನು ಬೇಕಾದರೂ ಕೇಳಿ.', line: 'ಬ್ಯಾಲೆನ್ಸ್, ಖರ್ಚು, ಸಾಲ ಮತ್ತು ಬಡ್ಡಿ ದರಗಳು, ನಿಮ್ಮ ಖಾತೆಯಿಂದ, ನಿಮ್ಮ ಭಾಷೆಯಲ್ಲಿ.' },
  hinglish: { title: 'Apne bank se kuch bhi poocho.', line: 'Balance, kharcha, loan aur rates — aapke asli account se, aapki bhasha mein.' },
}
