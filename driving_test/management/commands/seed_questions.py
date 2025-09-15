import re
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from driving_test.models import QuestionCategory, Question, AnswerOption

class Command(BaseCommand):
    help = 'Seed the database with driving test questions in Kinyarwanda'

    def handle(self, *args, **options):
        # Create a default admin user if it doesn't exist
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Created admin user'))

        # Create question categories
        categories_data = [
            {
                'name': 'Amategeko Rusange',
                'description': 'General driving laws and regulations'
            },
            {
                'name': 'Ibimenyetso by\'Umuhanda',
                'description': 'Road signs and traffic signals'
            },
            {
                'name': 'Umutekano mu muhanda',
                'description': 'Driving safety and vehicle maintenance'
            },
            {
                'name': 'Amategeko y\'Umuvuduko',
                'description': 'Speed limits and regulations'
            },
            {
                'name': 'Ibinyabiziga n\'Uburemere',
                'description': 'Vehicle specifications and weight limits'
            },
            {
                'name': 'Amatara n\'Ibimenyetso',
                'description': 'Lights and visibility requirements'
            }
        ]

        for cat_data in categories_data:
            category, created = QuestionCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')

        # Questions data from the document
        questions_data = [
            {
                'text': 'Ikinyabiziga cyose cyangwa ibinyabiziga bigenda bigomba kugira:',
                'options': [
                    'Umuyobozi',
                    'Umuherekeza', 
                    'A na B ni ibisubizo by\'ukuri',
                    'Nta gisubizo cy\'ukuri kirimo'
                ],
                'correct': 2,  # Index of correct answer (c)
                'category': 'Amategeko Rusange',
                'difficulty': 'easy'
            },
            {
                'text': 'Ijambo "akayira" bivuga inzira nyabagendwa ifunganye yagenewe gusa:',
                'options': [
                    'Abanyamaguru',
                    'Ibinyabiziga bigendera ku biziga bibiri',
                    'A na B ni ibisubizo by\'ukuri',
                    'Nta gisubizo cy\'ukuri kirimo'
                ],
                'correct': 2,  # Index of correct answer (c)
                'category': 'Ibimenyetso by\'Umuhanda',
                'difficulty': 'medium'
            },
            {
                'text': 'Umurongo uciyemo uduce umenyesha ahegereye umurongo ushobora kuzuzwa n\'uturanga gukata tw\'ibara ryera utwo turanga cyerekezo tumenyesha:',
                'options': [
                    'Igisate cy\'umuhanda abayobozi bagomba gukurikira',
                    'Ahegereye umurongo ukomeje',
                    'Igabanurwa ry\'umubare w\'ibisate by\'umuhanda mu cyerekezo bajyamo',
                    'A na C nibyo'
                ],
                'correct': 3,  # Index of correct answer (d)
                'category': 'Ibimenyetso by\'Umuhanda',
                'difficulty': 'hard'
            },
            {
                'text': 'Ahantu ho kugendera mu muhanda herekanwa n\'ibimenyetso bimurika ibinyabiziga ntibishobora kuhagenda:',
                'options': [
                    'Biteganye',
                    'Ku murongo umwe',
                    'A na B nibyo',
                    'Nta gisubizo cy\'ukuri kirimo'
                ],
                'correct': 3,  # Index of correct answer (d)
                'category': 'Ibimenyetso by\'Umuhanda',
                'difficulty': 'medium'
            },
            {
                'text': 'Ibinyabiziga bikurikira bigomba gukorerwa isuzumwa buri mwaka:',
                'options': [
                    'Ibinyabiziga bigenewe gutwara abagenzi muri rusange',
                    'Ibinyabiziga bigenewe gutwara ibintu birengeje toni 3.5',
                    'Ibinyabiziga bigenewe kwigisha gutwara',
                    'Nta gisubizo cy\'ukuri kirimo'
                ],
                'correct': 3,  # Index of correct answer (d)
                'category': 'Umutekano mu muhanda',
                'difficulty': 'medium'
            },
            {
                'text': 'Ubugari bwa romoruki ikuruwe n\'ikinyamitende itatu ntibugomba kurenza ibipimo bikurikira:',
                'options': [
                    'cm75',
                    'cm125',
                    'cm265',
                    'Nta gisubizo cy\'ukuri'
                ],
                'correct': 3,  # Index of correct answer (d)
                'category': 'Ibinyabiziga n\'Uburemere',
                'difficulty': 'hard'
            },
            {
                'text': 'Uburebure bw\'ibinyabiziga bikurikira ntibugomba kurenga metero 11:',
                'options': [
                    'Ibifite umutambiko umwe uhuza imipira',
                    'Ibifite imitambiko ibiri ikurikiranye mu bugari bwayo',
                    'Makuzungu',
                    'Nta gisubizo cy\'ukuri'
                ],
                'correct': 3,  # Index of correct answer (d)
                'category': 'Ibinyabiziga n\'Uburemere',
                'difficulty': 'hard'
            },
            {
                'text': 'Ikinyabiziga kibujijwe guhagarara akanya kanini aha hakurikira:',
                'options': [
                    'Ahatarengeje metero 1 imbere cyangwa inyuma y\'ikinyabiziga gihagaze akanya gato cyangwa kanini',
                    'Ahantu hari ibimenyetso bibuza byabugenewe',
                    'Aho abanyamaguru banyura mu muhanda ngo bakikire inkomyi',
                    'Ibisubizo byose nibyo'
                ],
                'correct': 3,  # Index of correct answer (d)
                'category': 'Amategeko Rusange',
                'difficulty': 'medium'
            },
            {
                'text': 'Kunyuranaho bikorerwa:',
                'options': [
                    'Mu ruhande rw\'iburyo gusa',
                    'Igihe cyose ni ibumoso',
                    'Iburyo iyo unyura ku nyamaswa',
                    'Nta gisubizo cy\'ukuri kirimo'
                ],
                'correct': 3,  # Index of correct answer (d)
                'category': 'Amategeko Rusange',
                'difficulty': 'easy'
            },
            {
                'text': 'Icyapa cyerekana umuvuduko ntarengwa ikinyabiziga kitagomba kurenza gishyirwa gusa ku binyabiziga bifite uburemere ntarengwa bukurikira:',
                'options': [
                    'Burenga toni 1',
                    'Burenga toni 2',
                    'Burenga toni 24',
                    'Nta gisubizo cy\'ukuri kirimo'
                ],
                'correct': 3,  # Index of correct answer (d)
                'category': 'Amategeko y\'Umuvuduko',
                'difficulty': 'hard'
            },
            {
                'text': 'Ahatari mu nsisiro umuvuduko ntarengwa mu isaha wa velomoteri ni:',
                'options': [
                    'Km50',
                    'Km40',
                    'Km30',
                    'Nta gisubizo cy\'ukuri'
                ],
                'correct': 0,  # Index of correct answer (a)
                'category': 'Amategeko y\'Umuvuduko',
                'difficulty': 'easy'
            },
            {
                'text': 'Umuyobozi ugenda mu muhanda igihe ubugari bwawo budatuma anyuranaho nta nkomyi ashobora kunyura mu kayira k\'abanyamaguru ariko amaze kureba ibi bikurikira:',
                'options': [
                    'Umuvuduko w\'abanyamaguru',
                    'Ubugari bw\'umuhanda',
                    'Umubare w\'abanyamaguru',
                    'Nta gisubizo cy\'ukuri kirimo'
                ],
                'correct': 3,  # Index of correct answer (d)
                'category': 'Amategeko Rusange',
                'difficulty': 'medium'
            },
            {
                'text': 'Ku byerekeye kwerekana ibinyabiziga n\'ukumurika kwabyo ndetse no kwerekana ihindura ry\'ibyerekezo byabyo. Birabujijwe gukora andi matara cyangwa utugarurarumuri uretse ibitegetswe ariko ntibireba amatara akurikira:',
                'options': [
                    'Amatara ndanga',
                    'Amatara ari imbere mu modoka',
                    'Amatara ndangaburambarare',
                    'Ibisubizo byose nibyo'
                ],
                'correct': 1,  # Index of correct answer (b)
                'category': 'Amatara n\'Ibimenyetso',
                'difficulty': 'hard'
            },
            {
                'text': 'Iyo nta mategeko awugabanya by\'umwihariko umuvuduko ntarengwa w\'amapikipiki mu isaha ni:',
                'options': [
                    'Km25',
                    'Km70',
                    'Km40',
                    'Nta gisubizo cy\'ukuri kirimo'
                ],
                'correct': 3,  # Index of correct answer (d)
                'category': 'Amategeko y\'Umuvuduko',
                'difficulty': 'medium'
            },
            {
                'text': 'Uburyo bukoreshwa kugirango ikinyabiziga kigende gahoro igihe feri idakora neza babwita:',
                'options': [
                    'Feri y\'urugendo',
                    'Feri yo guhagarara umwanya munini',
                    'Feri yo gutabara',
                    'Nta gisubizo cy\'ukuri kirimo'
                ],
                'correct': 2,  # Index of correct answer (c)
                'category': 'Umutekano mu muhanda',
                'difficulty': 'medium'
            },
            {
                'text': 'Nibura ikinyabiziga gitegetswe kugira uduhanagurakirahure tungahe:',
                'options': [
                    '2',
                    '3',
                    '1',
                    'Nta gisubizo cy\'ukuri kirimo'
                ],
                'correct': 2,  # Index of correct answer (c)
                'category': 'Umutekano mu muhanda',
                'difficulty': 'easy'
            },
            {
                'text': 'Amatara maremare y\'ikinyabiziga agomba kuzimwa mu bihe bikurikira:',
                'options': [
                    'Iyo umuhanda umurikiye umuyobozi abasha kureba muri metero 20',
                    'Iyo ikinyabiziga kigiye kubisikana n\'ibindi',
                    'Iyo ari mu nsisiro',
                    'Ibisubizo byose ni ukuri'
                ],
                'correct': 1,  # Index of correct answer (b)
                'category': 'Amatara n\'Ibimenyetso',
                'difficulty': 'medium'
            },
            {
                'text': 'Ikinyabiziga ntigishobora kugira amatara arenga abiri y\'ubwoko bumwe keretse kubyerekeye amatara akurikira:',
                'options': [
                    'Itara ndangamubyimba',
                    'Itara ryerekana icyerekezo',
                    'Itara ndangaburumbarare',
                    'Ibisubizo byose ni ukuri'
                ],
                'correct': 3,  # Index of correct answer (d)
                'category': 'Amatara n\'Ibimenyetso',
                'difficulty': 'hard'
            },
            {
                'text': 'Ubugari bwa romoruki ikuruwe n\'igare cyangwa velomoteri ntiburenza ibipimo bikurikira:',
                'options': [
                    'cm25',
                    'cm125',
                    'cm45',
                    'Nta gisubizo cy\'ukuri kirimo'
                ],
                'correct': 3,  # Index of correct answer (d)
                'category': 'Ibinyabiziga n\'Uburemere',
                'difficulty': 'medium'
            },
            {
                'text': 'Ibinyabiziga bikoreshwa nka tagisi, bitegerereza abantu mu nzira nyabagendwa, bishobora gushyirwaho itara ryerekana ko ikinyabiziga kitakodeshejwe. Iryo tara rishyirwaho ku buryo bukurikira:',
                'options': [
                    'Ni itara ry\'icyatsi rishyirwa imbere ku kinyabiziga',
                    'Ni itara ry\'icyatsi rishyirwa ibumoso',
                    'Ni itara ry\'umuhondo rishyirwa inyuma',
                    'A na C ni ibisubizo by\'ukuri'
                ],
                'correct': 0,  # Index of correct answer (a)
                'category': 'Amatara n\'Ibimenyetso',
                'difficulty': 'medium'
            }
        ]

        # Add more questions to reach a good number for testing
        additional_questions = [
            {
                'text': 'Za otobisi zagenewe gutwara abanyeshuri zishobora gushyirwaho amatara abiri asa n\'icunga rihishije amyasa kugirango yerekane ko zihagaze no kwerekana ko bagomba kwitonda:',
                'options': [
                    'Amatara abiri ashyirwa inyuma',
                    'Amatara abiri ashyirwa imbere',
                    'Rimwe rishyirwa imbere irindi inyuma',
                    'b na c ni ibisubizo by\'ukuri'
                ],
                'correct': 2,  # Index of correct answer (c)
                'category': 'Amatara n\'Ibimenyetso',
                'difficulty': 'medium'
            },
            {
                'text': 'Itara ryo guhagarara ry\'ibara ritukura rigomba kugaragara igihe ijuru rikeye nibura mu ntera ikurikira:',
                'options': [
                    'Metero 100 ku manywa na metero 20 mu ijoro',
                    'Metero 150 ku manywa na metero50 mu ijoro',
                    'Metero 200 ku manywa na metero100 mu ijoro',
                    'Nta gisubizo cy\'ukuri kirimo'
                ],
                'correct': 3,  # Index of correct answer (d)
                'category': 'Amatara n\'Ibimenyetso',
                'difficulty': 'hard'
            },
            {
                'text': 'Iyo umuvuduko w\'ibinyabiziga bidapakiye ushobora kurenga km50 mu isaha ahategamye, bigomba kuba bifite ibikoresho by\'ihoni byumvikanira mu ntera:',
                'options': [
                    'Metero 100',
                    'Metero 200',
                    'Metero 50',
                    'Metero 150'
                ],
                'correct': 2,  # Index of correct answer (c)
                'category': 'Umutekano mu muhanda',
                'difficulty': 'medium'
            },
            {
                'text': 'Iyo hatarimo indi myanya birabujijwe gutwara ku ntebe y\'imbere y\'imodoka abana badafite imyaka:',
                'options': [
                    'Imyaka 10',
                    'Imyaka 12',
                    'Imyaka 7',
                    'Ntagisubizo cy\'ukuri kirimo'
                ],
                'correct': 1,  # Index of correct answer (b)
                'category': 'Umutekano mu muhanda',
                'difficulty': 'easy'
            },
            {
                'text': 'Iyo nta mategeko awugabanya by\'umwihariko, umuvuduko ntarengwa ku modoka zitwara abagenzi mu buryo bwa rusange ni:',
                'options': [
                    'Km 60 mu isaha',
                    'Km 40 mu isaha',
                    'Km 25 mu isaha',
                    'Km20 mu isaha'
                ],
                'correct': 0,  # Index of correct answer (a)
                'category': 'Amategeko y\'Umuvuduko',
                'difficulty': 'easy'
            },
            {
                'text': 'Iyo nta mategeko awugabanya by\'umwihariko, umuvuduko ntarengwa ku modoka zikoreshwa nk\'amavatiri y\'ifasi cyangwa amatagisi zifite uburemere bwemewe butarenga kilogarama 3500 ni:',
                'options': [
                    'Km 60 mu isaha',
                    'Km 40 mu isaha',
                    'Km 75 mu isaha',
                    'Km20 mu isaha'
                ],
                'correct': 2,  # Index of correct answer (c)
                'category': 'Amategeko y\'Umuvuduko',
                'difficulty': 'medium'
            }
        ]

        # Combine all questions
        all_questions = questions_data + additional_questions

        # Create questions and answer options
        for q_data in all_questions:
            # Get the category
            try:
                category = QuestionCategory.objects.get(name=q_data['category'])
            except QuestionCategory.DoesNotExist:
                category = QuestionCategory.objects.first()  # Fallback

            # Create question
            question, created = Question.objects.get_or_create(
                question_text=q_data['text'],
                defaults={
                    'category': category,
                    'difficulty': q_data['difficulty'],
                    'created_by': admin_user,
                    'is_active': True
                }
            )

            if created:
                # Create answer options
                for i, option_text in enumerate(q_data['options']):
                    AnswerOption.objects.create(
                        question=question,
                        option_text=option_text,
                        is_correct=(i == q_data['correct']),
                        order=i
                    )
                self.stdout.write(f'Created question: {question.question_text[:50]}...')

        total_questions = Question.objects.count()
        total_categories = QuestionCategory.objects.count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully seeded database with {total_questions} questions '
                f'across {total_categories} categories'
            )
        )
        
        # Display summary
        self.stdout.write('\nCategories created:')
        for category in QuestionCategory.objects.all():
            question_count = category.questions.count()
            self.stdout.write(f'  - {category.name}: {question_count} questions')
        
        self.stdout.write(f'\nAdmin user credentials:')
        self.stdout.write(f'  Username: admin')
        self.stdout.write(f'  Password: admin123')