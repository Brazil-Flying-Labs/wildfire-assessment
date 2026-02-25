import { useLanguage } from "../../context/LanguageContext";

const TERMS_DATE = "2026-02-25";

const content = {
  en: {
    intro: [
      'Welcome to the Wildfire Damage Assessment Platform ("Platform"), operated by Brazil Flying Labs.',
      "By creating an account or using the Platform, you agree to these Terms of Service. These Terms are designed to ensure transparency, responsible use, and protection of your data.",
    ],
    sections: [
      {
        title: "1. About the Platform",
        blocks: [
          "The Platform provides wildfire damage assessment tools using satellite imagery and geospatial analysis. It enables authorized users to:",
          [
            "Analyze burn severity",
            "Generate scientific outputs",
            "Access AI-assisted analytical reports",
            "Monitor environmental recovery over time",
          ],
          "Access may be limited to specific countries or regions, depending on authorization.",
        ],
      },
      {
        title: "2. Access and Accounts",
        blocks: [
          [
            "Access requires authentication via Auth0.",
            "Account activation is subject to administrator approval.",
            "Access permissions may be granted on a per-country basis.",
            "You are responsible for maintaining the confidentiality of your login credentials.",
            "The Platform must be used only for legitimate professional, research, or public-interest purposes related to environmental monitoring.",
          ],
          "If misuse, security risks, or legal concerns arise, Brazil Flying Labs may restrict or suspend access to protect users and the integrity of the Platform.",
        ],
      },
      {
        title: "3. Usage Analytics and Technical Monitoring",
        blocks: [
          "To ensure reliability, security, and continuous improvement, the Platform collects limited technical telemetry data, including:",
          [
            "Page views and navigation flow",
            "Interaction events (e.g., button clicks, form submissions)",
            "Browser type, device type, and screen resolution",
            "Performance metrics and error logs",
          ],
          "This telemetry is:",
          [
            "Used exclusively for system monitoring, debugging, performance optimization, and usability improvements",
            "Aggregated and anonymized",
            "Not used for profiling or marketing",
            "Not sold or shared for commercial purposes",
          ],
          "We do not transmit personal data (such as names, email addresses, or account identifiers) to analytics or monitoring services.",
          "Technical telemetry is processed through trusted service providers, including PostHog and Grafana Cloud, solely for operational monitoring purposes.",
        ],
      },
      {
        title: "4. Data Storage and Security",
        blocks: [
          "Platform data is hosted on secure cloud infrastructure (Amazon Web Services) with:",
          [
            "Encryption in transit (TLS)",
            "Encryption at rest",
            "Role-based access controls",
          ],
          "Geospatial data and analysis outputs are associated with your account for retrieval and historical reference.",
          "We implement appropriate technical and organizational measures to protect personal data. However, no digital system can guarantee absolute security.",
        ],
      },
      {
        title: "5. Data Protection and Privacy (LGPD & GDPR)",
        blocks: [
          "Brazil Flying Labs acts as the Data Controller for personal data processed through the Platform.",
          "We comply with:",
          [
            "Brazilian General Data Protection Law (LGPD \u2013 Law No. 13,709/2018)",
            "European Union General Data Protection Regulation (GDPR)",
          ],
          { subtitle: "Legal Basis for Processing" },
          "Personal data is processed based on:",
          [
            "Performance of this agreement",
            "Your consent (where required)",
            "Legitimate interest in ensuring platform functionality, security, and improvement",
          ],
          { subtitle: "Your Rights" },
          "Where applicable, you may exercise the following rights:",
          [
            "Access your personal data",
            "Request correction of inaccurate data",
            "Request deletion (subject to legal retention requirements)",
            "Request data portability",
            "Withdraw consent",
            "Object to certain processing activities",
          ],
          "To exercise your rights or submit privacy-related inquiries, please contact:",
          "privacy@brazilflyinglabs.org.br",
          "We respond within legally required timeframes.",
        ],
      },
      {
        title: "6. Open Source and Licensing",
        blocks: [
          [
            "The Platform is open-source software released under the MIT License.",
            "The source code is publicly available.",
            "The Platform is provided free of charge.",
            "Satellite imagery (e.g., Sentinel-2 via Google Earth Engine) remains subject to its respective licenses.",
            "Analysis outputs may be used by authorized users for legitimate professional, academic, or public-interest purposes.",
            "Brazil Flying Labs may evolve, improve, or adapt the Platform over time.",
          ],
        ],
      },
      {
        title: "7. Responsible Use",
        blocks: [
          "You agree to:",
          [
            "Use the Platform lawfully and ethically",
            "Provide accurate analysis parameters",
            "Not attempt unauthorized access",
            "Not interfere with system integrity",
            "Not share account credentials",
          ],
          "These safeguards help maintain a secure and reliable environment for all users.",
        ],
      },
      {
        title: "8. Limitation of Liability",
        blocks: [
          'The Platform is provided "as is" without warranties of any kind.',
          "Analysis outputs are intended for scientific and informational purposes. Users remain responsible for validating results before making operational, policy, or financial decisions.",
          "Brazil Flying Labs shall not be liable for indirect or consequential damages arising from Platform use.",
        ],
      },
      {
        title: "9. Updates and Contact",
        blocks: [
          "We may update these Terms periodically to reflect operational, technical, or regulatory changes. When material changes occur, we will notify users through the Platform.",
          "Continued use after updates indicates acceptance of the revised Terms.",
          "For questions regarding these Terms or data protection matters, please contact:",
          "Brazil Flying Labs",
          "privacy@brazilflyinglabs.org.br",
        ],
      },
    ],
  },
  "pt-BR": {
    intro: [
      'Bem-vindo(a) \u00e0 Plataforma de Avalia\u00e7\u00e3o de Danos por Inc\u00eandios Florestais ("Plataforma"), operada pela Brazil Flying Labs.',
      "Ao criar uma conta ou utilizar a Plataforma, voc\u00ea concorda com estes Termos de Servi\u00e7o. Estes Termos foram elaborados para garantir transpar\u00eancia, uso respons\u00e1vel e prote\u00e7\u00e3o dos seus dados.",
    ],
    sections: [
      {
        title: "1. Sobre a Plataforma",
        blocks: [
          "A Plataforma fornece ferramentas de avalia\u00e7\u00e3o de danos por inc\u00eandios florestais utilizando imagens de sat\u00e9lite e an\u00e1lise geoespacial. Ela permite que usu\u00e1rios autorizados:",
          [
            "Analisem a severidade de queimadas",
            "Gerem produtos cient\u00edficos",
            "Acessem relat\u00f3rios anal\u00edticos assistidos por IA",
            "Monitorem a recupera\u00e7\u00e3o ambiental ao longo do tempo",
          ],
          "O acesso pode ser limitado a pa\u00edses ou regi\u00f5es espec\u00edficos, dependendo da autoriza\u00e7\u00e3o.",
        ],
      },
      {
        title: "2. Acesso e Contas",
        blocks: [
          [
            "O acesso requer autentica\u00e7\u00e3o via Auth0.",
            "A ativa\u00e7\u00e3o da conta est\u00e1 sujeita \u00e0 aprova\u00e7\u00e3o do administrador.",
            "As permiss\u00f5es de acesso podem ser concedidas por pa\u00eds.",
            "Voc\u00ea \u00e9 respons\u00e1vel por manter a confidencialidade das suas credenciais de login.",
            "A Plataforma deve ser utilizada apenas para fins profissionais, de pesquisa ou de interesse p\u00fablico leg\u00edtimos relacionados ao monitoramento ambiental.",
          ],
          "Em caso de uso indevido, riscos de seguran\u00e7a ou quest\u00f5es legais, a Brazil Flying Labs pode restringir ou suspender o acesso para proteger os usu\u00e1rios e a integridade da Plataforma.",
        ],
      },
      {
        title: "3. An\u00e1lise de Uso e Monitoramento T\u00e9cnico",
        blocks: [
          "Para garantir confiabilidade, seguran\u00e7a e melhoria cont\u00ednua, a Plataforma coleta dados de telemetria t\u00e9cnica limitados, incluindo:",
          [
            "Visualiza\u00e7\u00f5es de p\u00e1ginas e fluxo de navega\u00e7\u00e3o",
            "Eventos de intera\u00e7\u00e3o (ex.: cliques em bot\u00f5es, envio de formul\u00e1rios)",
            "Tipo de navegador, tipo de dispositivo e resolu\u00e7\u00e3o de tela",
            "M\u00e9tricas de desempenho e logs de erros",
          ],
          "Esta telemetria \u00e9:",
          [
            "Utilizada exclusivamente para monitoramento do sistema, depura\u00e7\u00e3o, otimiza\u00e7\u00e3o de desempenho e melhorias de usabilidade",
            "Agregada e anonimizada",
            "N\u00e3o utilizada para cria\u00e7\u00e3o de perfis ou marketing",
            "N\u00e3o vendida ou compartilhada para fins comerciais",
          ],
          "N\u00e3o transmitimos dados pessoais (como nomes, endere\u00e7os de e-mail ou identificadores de conta) para servi\u00e7os de an\u00e1lise ou monitoramento.",
          "A telemetria t\u00e9cnica \u00e9 processada por provedores de servi\u00e7o confi\u00e1veis, incluindo PostHog e Grafana Cloud, exclusivamente para fins de monitoramento operacional.",
        ],
      },
      {
        title: "4. Armazenamento e Seguran\u00e7a de Dados",
        blocks: [
          "Os dados da Plataforma s\u00e3o hospedados em infraestrutura de nuvem segura (Amazon Web Services) com:",
          [
            "Criptografia em tr\u00e2nsito (TLS)",
            "Criptografia em repouso",
            "Controles de acesso baseados em fun\u00e7\u00f5es",
          ],
          "Dados geoespaciais e resultados de an\u00e1lises s\u00e3o associados \u00e0 sua conta para consulta e refer\u00eancia hist\u00f3rica.",
          "Implementamos medidas t\u00e9cnicas e organizacionais apropriadas para proteger dados pessoais. No entanto, nenhum sistema digital pode garantir seguran\u00e7a absoluta.",
        ],
      },
      {
        title: "5. Prote\u00e7\u00e3o de Dados e Privacidade (LGPD e GDPR)",
        blocks: [
          "A Brazil Flying Labs atua como Controladora de Dados para os dados pessoais processados atrav\u00e9s da Plataforma.",
          "Cumprimos:",
          [
            "Lei Geral de Prote\u00e7\u00e3o de Dados (LGPD \u2013 Lei n\u00ba 13.709/2018)",
            "Regulamento Geral de Prote\u00e7\u00e3o de Dados da Uni\u00e3o Europeia (GDPR)",
          ],
          { subtitle: "Base Legal para o Processamento" },
          "Os dados pessoais s\u00e3o processados com base em:",
          [
            "Execu\u00e7\u00e3o deste contrato",
            "Seu consentimento (quando necess\u00e1rio)",
            "Interesse leg\u00edtimo em garantir a funcionalidade, seguran\u00e7a e melhoria da plataforma",
          ],
          { subtitle: "Seus Direitos" },
          "Quando aplic\u00e1vel, voc\u00ea pode exercer os seguintes direitos:",
          [
            "Acessar seus dados pessoais",
            "Solicitar corre\u00e7\u00e3o de dados imprecisos",
            "Solicitar exclus\u00e3o (sujeito a requisitos legais de reten\u00e7\u00e3o)",
            "Solicitar portabilidade de dados",
            "Revogar consentimento",
            "Opor-se a determinadas atividades de processamento",
          ],
          "Para exercer seus direitos ou enviar consultas relacionadas \u00e0 privacidade, entre em contato:",
          "privacy@brazilflyinglabs.org.br",
          "Respondemos dentro dos prazos legalmente exigidos.",
        ],
      },
      {
        title: "6. C\u00f3digo Aberto e Licenciamento",
        blocks: [
          [
            "A Plataforma \u00e9 um software de c\u00f3digo aberto distribu\u00eddo sob a Licen\u00e7a MIT.",
            "O c\u00f3digo-fonte est\u00e1 dispon\u00edvel publicamente.",
            "A Plataforma \u00e9 fornecida gratuitamente.",
            "Imagens de sat\u00e9lite (ex.: Sentinel-2 via Google Earth Engine) permanecem sujeitas \u00e0s suas respectivas licen\u00e7as.",
            "Os resultados de an\u00e1lises podem ser utilizados por usu\u00e1rios autorizados para fins profissionais, acad\u00eamicos ou de interesse p\u00fablico leg\u00edtimos.",
            "A Brazil Flying Labs pode evoluir, melhorar ou adaptar a Plataforma ao longo do tempo.",
          ],
        ],
      },
      {
        title: "7. Uso Respons\u00e1vel",
        blocks: [
          "Voc\u00ea concorda em:",
          [
            "Utilizar a Plataforma de forma legal e \u00e9tica",
            "Fornecer par\u00e2metros de an\u00e1lise precisos",
            "N\u00e3o tentar acesso n\u00e3o autorizado",
            "N\u00e3o interferir na integridade do sistema",
            "N\u00e3o compartilhar credenciais de conta",
          ],
          "Essas salvaguardas ajudam a manter um ambiente seguro e confi\u00e1vel para todos os usu\u00e1rios.",
        ],
      },
      {
        title: "8. Limita\u00e7\u00e3o de Responsabilidade",
        blocks: [
          "A Plataforma \u00e9 fornecida \"como est\u00e1\" sem garantias de qualquer tipo.",
          "Os resultados de an\u00e1lises s\u00e3o destinados a fins cient\u00edficos e informativos. Os usu\u00e1rios permanecem respons\u00e1veis por validar os resultados antes de tomar decis\u00f5es operacionais, pol\u00edticas ou financeiras.",
          "A Brazil Flying Labs n\u00e3o ser\u00e1 respons\u00e1vel por danos indiretos ou consequenciais decorrentes do uso da Plataforma.",
        ],
      },
      {
        title: "9. Atualiza\u00e7\u00f5es e Contato",
        blocks: [
          "Podemos atualizar estes Termos periodicamente para refletir mudan\u00e7as operacionais, t\u00e9cnicas ou regulat\u00f3rias. Quando ocorrerem altera\u00e7\u00f5es significativas, notificaremos os usu\u00e1rios atrav\u00e9s da Plataforma.",
          "O uso cont\u00ednuo ap\u00f3s as atualiza\u00e7\u00f5es indica aceita\u00e7\u00e3o dos Termos revisados.",
          "Para perguntas sobre estes Termos ou quest\u00f5es de prote\u00e7\u00e3o de dados, entre em contato:",
          "Brazil Flying Labs",
          "privacy@brazilflyinglabs.org.br",
        ],
      },
    ],
  },
  fr: {
    intro: [
      "Bienvenue sur la Plateforme d'\u00c9valuation des Dommages par Incendies de For\u00eat (\u00ab Plateforme \u00bb), exploit\u00e9e par Brazil Flying Labs.",
      "En cr\u00e9ant un compte ou en utilisant la Plateforme, vous acceptez ces Conditions d'Utilisation. Ces Conditions sont con\u00e7ues pour garantir la transparence, une utilisation responsable et la protection de vos donn\u00e9es.",
    ],
    sections: [
      {
        title: "1. \u00c0 propos de la Plateforme",
        blocks: [
          "La Plateforme fournit des outils d'\u00e9valuation des dommages par incendies de for\u00eat utilisant l'imagerie satellite et l'analyse g\u00e9ospatiale. Elle permet aux utilisateurs autoris\u00e9s de :",
          [
            "Analyser la gravit\u00e9 des br\u00fblures",
            "G\u00e9n\u00e9rer des productions scientifiques",
            "Acc\u00e9der \u00e0 des rapports analytiques assist\u00e9s par IA",
            "Surveiller la r\u00e9cup\u00e9ration environnementale au fil du temps",
          ],
          "L'acc\u00e8s peut \u00eatre limit\u00e9 \u00e0 des pays ou r\u00e9gions sp\u00e9cifiques, selon l'autorisation.",
        ],
      },
      {
        title: "2. Acc\u00e8s et Comptes",
        blocks: [
          [
            "L'acc\u00e8s n\u00e9cessite une authentification via Auth0.",
            "L'activation du compte est soumise \u00e0 l'approbation de l'administrateur.",
            "Les permissions d'acc\u00e8s peuvent \u00eatre accord\u00e9es par pays.",
            "Vous \u00eates responsable de la confidentialit\u00e9 de vos identifiants de connexion.",
            "La Plateforme doit \u00eatre utilis\u00e9e uniquement \u00e0 des fins professionnelles, de recherche ou d'int\u00e9r\u00eat public l\u00e9gitimes li\u00e9es \u00e0 la surveillance environnementale.",
          ],
          "En cas d'utilisation abusive, de risques de s\u00e9curit\u00e9 ou de pr\u00e9occupations juridiques, Brazil Flying Labs peut restreindre ou suspendre l'acc\u00e8s pour prot\u00e9ger les utilisateurs et l'int\u00e9grit\u00e9 de la Plateforme.",
        ],
      },
      {
        title: "3. Analyses d'Utilisation et Surveillance Technique",
        blocks: [
          "Pour garantir la fiabilit\u00e9, la s\u00e9curit\u00e9 et l'am\u00e9lioration continue, la Plateforme collecte des donn\u00e9es de t\u00e9l\u00e9m\u00e9trie technique limit\u00e9es, notamment :",
          [
            "Pages consult\u00e9es et flux de navigation",
            "\u00c9v\u00e9nements d'interaction (ex. : clics sur boutons, soumissions de formulaires)",
            "Type de navigateur, type d'appareil et r\u00e9solution d'\u00e9cran",
            "M\u00e9triques de performance et journaux d'erreurs",
          ],
          "Cette t\u00e9l\u00e9m\u00e9trie est :",
          [
            "Utilis\u00e9e exclusivement pour la surveillance du syst\u00e8me, le d\u00e9bogage, l'optimisation des performances et les am\u00e9liorations de convivialit\u00e9",
            "Agr\u00e9g\u00e9e et anonymis\u00e9e",
            "Non utilis\u00e9e pour le profilage ou le marketing",
            "Non vendue ni partag\u00e9e \u00e0 des fins commerciales",
          ],
          "Nous ne transmettons pas de donn\u00e9es personnelles (telles que noms, adresses e-mail ou identifiants de compte) aux services d'analyse ou de surveillance.",
          "La t\u00e9l\u00e9m\u00e9trie technique est trait\u00e9e par des fournisseurs de services de confiance, notamment PostHog et Grafana Cloud, uniquement \u00e0 des fins de surveillance op\u00e9rationnelle.",
        ],
      },
      {
        title: "4. Stockage et S\u00e9curit\u00e9 des Donn\u00e9es",
        blocks: [
          "Les donn\u00e9es de la Plateforme sont h\u00e9berg\u00e9es sur une infrastructure cloud s\u00e9curis\u00e9e (Amazon Web Services) avec :",
          [
            "Chiffrement en transit (TLS)",
            "Chiffrement au repos",
            "Contr\u00f4les d'acc\u00e8s bas\u00e9s sur les r\u00f4les",
          ],
          "Les donn\u00e9es g\u00e9ospatiales et les r\u00e9sultats d'analyse sont associ\u00e9s \u00e0 votre compte pour consultation et r\u00e9f\u00e9rence historique.",
          "Nous mettons en \u0153uvre des mesures techniques et organisationnelles appropri\u00e9es pour prot\u00e9ger les donn\u00e9es personnelles. Cependant, aucun syst\u00e8me num\u00e9rique ne peut garantir une s\u00e9curit\u00e9 absolue.",
        ],
      },
      {
        title: "5. Protection des Donn\u00e9es et Confidentialit\u00e9 (LGPD et RGPD)",
        blocks: [
          "Brazil Flying Labs agit en tant que Responsable du Traitement des donn\u00e9es personnelles trait\u00e9es via la Plateforme.",
          "Nous respectons :",
          [
            "Loi G\u00e9n\u00e9rale sur la Protection des Donn\u00e9es du Br\u00e9sil (LGPD \u2013 Loi n\u00b0 13 709/2018)",
            "R\u00e8glement G\u00e9n\u00e9ral sur la Protection des Donn\u00e9es de l'Union Europ\u00e9enne (RGPD)",
          ],
          { subtitle: "Base Juridique du Traitement" },
          "Les donn\u00e9es personnelles sont trait\u00e9es sur la base de :",
          [
            "L'ex\u00e9cution de cet accord",
            "Votre consentement (lorsque requis)",
            "L'int\u00e9r\u00eat l\u00e9gitime \u00e0 assurer la fonctionnalit\u00e9, la s\u00e9curit\u00e9 et l'am\u00e9lioration de la plateforme",
          ],
          { subtitle: "Vos Droits" },
          "Le cas \u00e9ch\u00e9ant, vous pouvez exercer les droits suivants :",
          [
            "Acc\u00e9der \u00e0 vos donn\u00e9es personnelles",
            "Demander la correction de donn\u00e9es inexactes",
            "Demander la suppression (sous r\u00e9serve des exigences l\u00e9gales de conservation)",
            "Demander la portabilit\u00e9 des donn\u00e9es",
            "Retirer votre consentement",
            "Vous opposer \u00e0 certaines activit\u00e9s de traitement",
          ],
          "Pour exercer vos droits ou soumettre des demandes relatives \u00e0 la confidentialit\u00e9, veuillez contacter :",
          "privacy@brazilflyinglabs.org.br",
          "Nous r\u00e9pondons dans les d\u00e9lais l\u00e9galement requis.",
        ],
      },
      {
        title: "6. Code Ouvert et Licence",
        blocks: [
          [
            "La Plateforme est un logiciel open source distribu\u00e9 sous la Licence MIT.",
            "Le code source est publiquement disponible.",
            "La Plateforme est fournie gratuitement.",
            "L'imagerie satellite (ex. : Sentinel-2 via Google Earth Engine) reste soumise \u00e0 ses licences respectives.",
            "Les r\u00e9sultats d'analyse peuvent \u00eatre utilis\u00e9s par les utilisateurs autoris\u00e9s \u00e0 des fins professionnelles, acad\u00e9miques ou d'int\u00e9r\u00eat public l\u00e9gitimes.",
            "Brazil Flying Labs peut faire \u00e9voluer, am\u00e9liorer ou adapter la Plateforme au fil du temps.",
          ],
        ],
      },
      {
        title: "7. Utilisation Responsable",
        blocks: [
          "Vous acceptez de :",
          [
            "Utiliser la Plateforme de mani\u00e8re l\u00e9gale et \u00e9thique",
            "Fournir des param\u00e8tres d'analyse pr\u00e9cis",
            "Ne pas tenter un acc\u00e8s non autoris\u00e9",
            "Ne pas interf\u00e9rer avec l'int\u00e9grit\u00e9 du syst\u00e8me",
            "Ne pas partager vos identifiants de compte",
          ],
          "Ces mesures de protection contribuent \u00e0 maintenir un environnement s\u00e9curis\u00e9 et fiable pour tous les utilisateurs.",
        ],
      },
      {
        title: "8. Limitation de Responsabilit\u00e9",
        blocks: [
          "La Plateforme est fournie \u00ab en l'\u00e9tat \u00bb sans garantie d'aucune sorte.",
          "Les r\u00e9sultats d'analyse sont destin\u00e9s \u00e0 des fins scientifiques et informatives. Les utilisateurs restent responsables de la validation des r\u00e9sultats avant de prendre des d\u00e9cisions op\u00e9rationnelles, politiques ou financi\u00e8res.",
          "Brazil Flying Labs ne sera pas responsable des dommages indirects ou cons\u00e9cutifs r\u00e9sultant de l'utilisation de la Plateforme.",
        ],
      },
      {
        title: "9. Mises \u00e0 Jour et Contact",
        blocks: [
          "Nous pouvons mettre \u00e0 jour ces Conditions p\u00e9riodiquement pour refl\u00e9ter des changements op\u00e9rationnels, techniques ou r\u00e9glementaires. Lorsque des modifications importantes surviennent, nous en informerons les utilisateurs via la Plateforme.",
          "L'utilisation continue apr\u00e8s les mises \u00e0 jour indique l'acceptation des Conditions r\u00e9vis\u00e9es.",
          "Pour toute question concernant ces Conditions ou les questions de protection des donn\u00e9es, veuillez contacter :",
          "Brazil Flying Labs",
          "privacy@brazilflyinglabs.org.br",
        ],
      },
    ],
  },
};

function TermsContent() {
  const { language } = useLanguage();
  const terms = content[language] || content.en;

  return (
    <div className="terms-text">
      <p className="terms-date">
        <small className="text-muted">
          {language === "pt-BR"
            ? `\u00daltima atualiza\u00e7\u00e3o: ${TERMS_DATE}`
            : language === "fr"
              ? `Derni\u00e8re mise \u00e0 jour : ${TERMS_DATE}`
              : `Last updated: ${TERMS_DATE}`}
        </small>
      </p>
      {terms.intro.map((text, i) => (
        <p key={`intro-${i}`}>{text}</p>
      ))}
      {terms.sections.map((section, i) => (
        <div key={i} className="terms-section">
          <h3>{section.title}</h3>
          {section.blocks.map((block, k) => {
            if (typeof block === "string") return <p key={k}>{block}</p>;
            if (Array.isArray(block))
              return (
                <ul key={k}>
                  {block.map((item, j) => (
                    <li key={j}>{item}</li>
                  ))}
                </ul>
              );
            if (block.subtitle)
              return (
                <h4 key={k} className="terms-subtitle">
                  {block.subtitle}
                </h4>
              );
            return null;
          })}
        </div>
      ))}
    </div>
  );
}

export default TermsContent;
