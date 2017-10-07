from __future__ import unicode_literals
import re
import json
import random

from django.db import models
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.validators import MaxValueValidator
from django.utils.translation import ugettext as _
from django.utils.timezone import now
from django.utils.encoding import python_2_unicode_compatible
from django.conf import settings

from model_utils.managers import InheritanceManager

temp = ''
rep_questions = ''
tot = []
easy_id = []
med_id = []
had_id = []


class CategoryManager(models.Manager):

    def new_category(self, category):

        #  \s+ is space which will be replaced by - in the category name
        new_category = self.create(category=re.sub('\s+', '-', category)
                                   .lower())

        new_category.save()
        return new_category


@python_2_unicode_compatible
class Category(models.Model):

    category = models.CharField(
        verbose_name=_("Category"),
        max_length=250, blank=True,
        unique=True, null=True)

    objects = CategoryManager()

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.category


@python_2_unicode_compatible
class SubCategory(models.Model):

    sub_category = models.CharField(
        verbose_name=_("Sub-Category"),
        max_length=250, blank=True, null=True)

    # category = models.ForeignKey(
    #     Category, null=True, blank=True,
    #     verbose_name=_("Category"))

    objects = CategoryManager()

    class Meta:
        verbose_name = _("Sub-Category")
        verbose_name_plural = _("Sub-Categories")

    def __str__(self):
        return self.sub_category


class Tag(models.Model):
    #  question = models.ManyToManyField(Question,related_name='Tag ')
    tag = models.CharField(max_length=100)

    def __str__(self):
        return self.tag


class QuestionsAttempt(models.Model):
    username = models.CharField(
        verbose_name=_("name"),
        max_length=50, blank=False)

    quizname = models.CharField(
        verbose_name=_("quiz_name"),
        max_length=50, blank=False)

    quizid = models.CharField(
        verbose_name=_("quiz_id"),
        max_length=50, blank=False)

    questions = models.CharField(
        verbose_name=_("questions list"),
        max_length=1000, blank=False)

    def __str__(self):
        return self.username + " - " + self.quizname


@python_2_unicode_compatible
class Quiz(models.Model):

    title = models.CharField(
        verbose_name=_("Title"),
        max_length=60, blank=False)

    description = models.TextField(
        verbose_name=_("Description"),
        blank=True, help_text=_("a description of the quiz"))

    url = models.SlugField(
        max_length=60, blank=False,
        help_text=_("a user friendly url"),
        verbose_name=_("user friendly url"))

    category = models.ForeignKey(
        Category, null=True, blank=True,
        verbose_name=_("Category"))

    random_order = models.BooleanField(
        blank=False, default=False,
        verbose_name=_("Random Order"),
        help_text=_("Display the questions in "
                    "a random order or as they "
                    "are set?"))
    Automated_questions = models.BooleanField(
        blank=False, default=False,
        verbose_name=_("Automated Questions"),
        help_text=_("Select the questions based "
                    "on our wish."))

    tag = models.ManyToManyField(
        Tag, null=True, blank=True, default=None,
        verbose_name=_("tag"))

    easy_questions = models.PositiveIntegerField(
        blank=True, default=0, null=True, verbose_name=_("Easy level"
                                                         "Questions"),
        help_text=_("Number of questions that you want to be easy."))

    medium_questions = models.PositiveIntegerField(
        blank=True, default=0, null=True, verbose_name=_("Middle level"
                                                         "Questions"),
        help_text=_("Number of questions that you want to be medium."))

    hard_questions = models.PositiveIntegerField(
        blank=True, default=0, null=True, verbose_name=_("Hard level"
                                                         "Questions"),
        help_text=_("Number of questions that you want to be hard."))

    max_questions = models.PositiveIntegerField(
        blank=True, null=True, verbose_name=_("Max Questions"),
        help_text=_("Number of questions to be answered on each attempt."))

    max_questions = models.PositiveIntegerField(
        blank=True, null=True, verbose_name=_("Max Questions"),
        help_text=_("Number of questions to be answered on each attempt."))

    answers_at_end = models.BooleanField(
        blank=False, default=False,
        help_text=_("Correct answer is NOT shown after question."
                    " Answers displayed at the end."),
        verbose_name=_("Answers at end"))

    exam_paper = models.BooleanField(
        blank=False, default=False,
        help_text=_("If yes, the result of each"
                    " attempt by a user will be"
                    " stored. Necessary for marking."),
        verbose_name=_("Exam Paper"))

    single_attempt = models.BooleanField(
        blank=False, default=False,
        help_text=_("If yes, only one attempt by"
                    " a user will be permitted."
                    " Non users cannot sit this exam."),
        verbose_name=_("Single Attempt"))

    pass_mark = models.SmallIntegerField(
        blank=True, default=0,
        verbose_name=_("Pass Mark"),
        help_text=_("Percentage required to pass exam."),
        validators=[MaxValueValidator(100)])

    success_text = models.TextField(
        blank=True, help_text=_("Displayed if user passes."),
        verbose_name=_("Success Text"))

    fail_text = models.TextField(
        verbose_name=_("Fail Text"),
        blank=True, help_text=_("Displayed if user fails."))

    draft = models.BooleanField(
        blank=True, default=False,
        verbose_name=_("Draft"),
        help_text=_("If yes, the quiz is not displayed"
                    " in the quiz list and can only be"
                    " taken by users who can edit"
                    " quizzes."))

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        self.url = re.sub('\s+', '-', self.url).lower()

        self.url = ''.join(letter for letter in self.url if
                           letter.isalnum() or letter == '-')

        if self.single_attempt is True:
            self.exam_paper = True

        if self.pass_mark > 100:
            raise ValidationError('%s is above 100' % self.pass_mark)

        #  doubt why using this here
        super(Quiz, self).save(force_insert, force_update, *args, **kwargs)

    class Meta:
        verbose_name = _("Quiz")
        verbose_name_plural = _("Quizzes")

    def __str__(self):
        return self.title

    def get_questions(self):
        return self.question_set.all().select_subclasses()

    @property
    def get_max_score(self):
        return self.get_questions().count()

    # def anon_score_id(self):
    #     return str(self.id) + "_score"

    # def anon_q_list(self):
    #     return str(self.id) + "_q_list"

    # def anon_q_data(self):
    #     return str(self.id) + "_data"


class ProgressManager(models.Manager):

    def new_progress(self, user):
        new_progress = self.create(user=user,
                                   score="")
        new_progress.save()
        return new_progress


class Progress(models.Model):
    """
    Progress is used to track an individual signed in users score on different
    quiz's and categories

    Data stored in csv using the format:
        category, score, possible, category, score, possible, ...
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             verbose_name=_("User"))

    quiz = models.ForeignKey(Quiz, verbose_name=_("Quiz"))

    attempts = models.IntegerField(verbose_name=_("Total Number Of Attempts"),
                                   default=0)
    passed_attempts = models.IntegerField(verbose_name=_("Successfull"
                                                         "Attempts"),
                                          default=0)

    best_score = models.IntegerField(verbose_name=_("Best Score"),
                                     default=0)
    quiz_maximum_marks = models.IntegerField(verbose_name=_("Maximum possible"
                                                            "marks"),
                                             default=0)

    answers_of_best_attempt = models.TextField(blank=True, default='{}',
                                               verbose_name=_("User Answers"))
    #  objects = ProgressManager()

    def __str__(self):
        return str(self.user)

    class Meta:
        verbose_name = _("User Progress")
        verbose_name_plural = _("User progress records")

    # @property
    # def list_all_cat_scores(self):
    #     """
    #     Returns a dict in which the key is the category name and the item is
    #     a list of three integers.

    #     The first is the number of questions correct,
    #     the second is the possible best score,
    #     the third is the percentage correct.

    #     The dict will have one key for every category that you have defined
    #     """
    #     score_before = self.score
    #     output = {}
    #     for cat in Category.objects.all():
    #         to_find = re.escape(cat.category) + r",(\d+),(\d+),"
    #         #  group 1 is score, group 2 is highest possible

    #         match = re.search(to_find, self.score, re.IGNORECASE)

    #         if match:
    #             score = int(match.group(1))
    #             possible = int(match.group(2))

    #             try:
    #                 percent = int(round((float(score) / float(possible))
    #                                     * 100))
    #             except:
    #                 percent = 0

    #             output[cat.category] = [score, possible, percent]

    #         else:  # if category has not been added yet, add it.
    #             self.score += cat.category + ",0,0,"
    #             output[cat.category] = [0, 0]

    #     if len(self.score) > len(score_before):
    #         # If a new category has been added, save changes.
    #         self.save()

    #     return output

    # def update_score(self, question, score_to_add=0, possible_to_add=0):
    #     """
    #     Pass in question object, amount to increase score
    #     and max possible.

    #     Does not return anything.
    #     """
    #     category_test = Category.objects.filter(category=question.category)\
    #                                     .exists()

    #     if any([item is False for item in [category_test,
    #                                        score_to_add,
    #                                        possible_to_add,
    #                                        isinstance(score_to_add, int),
    #                                        isinstance(possible_to_add, int)]]):
    #         return _("error"), _("category does not exist or invalid score")

    #     to_find = re.escape(str(question.category)) +\
    #         r",(?P<score>\d+),(?P<possible>\d+),"

    #     match = re.search(to_find, self.score, re.IGNORECASE)

    #     if match:
    #         updated_score = int(match.group('score')) + abs(score_to_add)
    #         updated_possible = int(match.group('possible')) +\
    #             abs(possible_to_add)

    #         new_score = ",".join(
    #             [
    #                 str(question.category),
    #                 str(updated_score),
    #                 str(updated_possible), ""
    #             ])

    #         # swap old score for the new one
    #         self.score = self.score.replace(match.group(), new_score)
    #         self.save()

    #     else:
    #         #  if not present but existing, add with the points passed in
    #         self.score += ",".join(
    #             [
    #                 str(question.category),
    #                 str(score_to_add),
    #                 str(possible_to_add),
    #                 ""
    #             ])
    #         self.save()

    def show_exams(self):
        """
        Finds the previous quizzes marked as 'exam papers'.
        Returns a queryset of complete exams.
        """
        return Sitting.objects.filter(user=self.user, complete=True)
class NoQuestionException(Exception):
    pass

class SittingManager(models.Manager):
    
    def new_sitting(self, user, quiz):
        

        from quiz.models import QuestionsAttempt, SubCategory
        global quiz_id, topics, easy, med, hard, easy_questions, med_questions
        global had_questions, eas_l, med_l, had_l, total_quesions_l
        global temp, rep_questions, tot, easy_id, med_id, had_id
        if quiz.random_order is True:
            question_set = quiz.question_set.all() \
                                            .select_subclasses() \
                                            .order_by('?')
        else:
            question_set = quiz.question_set.all() \
                                            .select_subclasses()

        question_set = [item.id for item in question_set]

        
        
        if len(question_set) == 0:
            quiz_id = quiz.id
            topics = Quiz.objects.filter(id=quiz_id).values_list('tag',
                                                                 flat=True)
            easy = Quiz.objects.values_list('easy_questions',
                                            flat=True).get(id=quiz_id)
            med = Quiz.objects.values_list('medium_questions',
                                           flat=True).get(id=quiz_id)
            hard = Quiz.objects.values_list('hard_questions',
                                            flat=True).get(id=quiz_id)
            eas_l, med_l, had_l, total_quesions_l = [], [], [], []

            # actual questions present in the database
            sub_easid = SubCategory.objects.filter(sub_category=''
                                                   'easy').values('id')
            sub_medid = SubCategory.objects.filter(sub_category=''
                                                   'medium').values('id')
            sub_hadid = SubCategory.objects.filter(sub_category=''
                                                   'hard').values('id')
            eas_l = list(set(Question.objects.filter(tag__in=topics,
                                                     sub_category=sub_easid[0]['id'])))
            med_l = list(set(Question.objects.filter(tag__in=topics,
                                                     sub_category=sub_medid[0]['id'])))
            had_l = list(set(Question.objects.filter(tag__in=topics,
                                                     sub_category=sub_hadid[0]['id'])))
            if QuestionsAttempt.objects.filter(username=user,
                                               quizid=quiz_id).exists() is True:
                rep_questions = QuestionsAttempt.objects.filter(username=user,
                                                                quizid=quiz_id).values('questions')

            else:
                rep_questions = ''
                temp = ''

            if rep_questions:
                rep_questions = rep_questions[0]['questions']
                rep_questions = rep_questions[:-1]
                rep_questions = [int(x) for x in rep_questions.split(',')]
                temp = ','.join(str(e) for e in rep_questions)
                temp += ','
                easy_id = [item.id for item in eas_l]
                med_id = [item.id for item in med_l]
                had_id = [item.id for item in had_l]
                easy_id = [x for x in easy_id if x not in rep_questions]
                med_id = [x for x in med_id if x not in rep_questions]
                had_id = [x for x in had_id if x not in rep_questions]
                eas_l = list(set(Question.objects.filter(id__in=easy_id,
                                                         sub_category=sub_easid[0]['id'])))
                med_l = list(set(Question.objects.filter(id__in=med_id, sub_category=sub_medid[0]['id'])))
                had_l = list(set(Question.objects.filter(id__in=had_id, sub_category=sub_hadid[0]['id'])))
            if easy <= len(eas_l):
                eas_l = sorted(eas_l, key=lambda k: random.random())[:easy]
            else:
                eas_l = sorted(eas_l, key=lambda k: random.random())[:len(eas_l)]
            if med <= len(med_l):
                med_l = sorted(med_l, key=lambda k: random.random())[:med]
            else:
                med_l = sorted(med_l, key=lambda k: random.random())[:len(med_l)]
            if hard <= len(had_l):
                had_l = sorted(had_l, key=lambda k: random.random())[:hard]
            else:
                had_l = sorted(had_l, key=lambda k: random.random())[:len(had_l)]
            total_quesions_l.extend(eas_l)
            total_quesions_l.extend(med_l)
            total_quesions_l.extend(had_l)
            tot = [item.id for item in total_quesions_l]
            if len(tot) == 0:
                raise NoQuestionException('You have attempted all the '
                                           'questions in our database '
                                           'related to your topics. please '
                                           'try with different topics.. ')

            check = QuestionsAttempt.objects.filter(username=user, quizid=quiz_id).exists()
            if check is False:
                s = QuestionsAttempt(username=user, quizname=quiz, quizid=quiz_id)
                s.save()
                # newquiz = s.quizid
                # newuser = s.username
                temp += ','.join(str(e) for e in tot)
                temp += ','
                obj = QuestionsAttempt.objects.get(username=user, quizid=quiz_id)
                obj.questions = temp
                obj.save()
                # rep_questions  = QuestionsAttempt.objects.filter(username=user, quizid=quiz_id).values('questions')
            if check is True:
                temp += ','.join(str(e) for e in tot)
                temp += ','
                obj = QuestionsAttempt.objects.get(username=user, quizid=quiz_id)
                obj.questions = temp
                obj.save()
                # rep_questions  = QuestionsAttempt.objects.filter(username=user, quizid=quiz_id).values('questions')

            # rep_questions = QuestionsAttempt.objects.values_list('questions', flat=True).get(username=user, quizid=quiz_id)

            question_set = tot
            questions = ",".join(map(str, tot)) + ","
        else:
            if quiz.max_questions and quiz.max_questions < len(question_set):
                question_set = question_set[:quiz.max_questions]
            questions = ",".join(map(str, question_set)) + ","

        new_sitting = self.create(user=user,
                                  quiz=quiz,
                                  question_order=questions,
                                  question_list=questions,
                                  incorrect_questions="",
                                  current_score=0,
                                  complete=False,
                                  user_answers='{}',
                                  total_questions=len(question_set) - 1)
        return new_sitting

    def user_sitting(self, user, quiz):
        if quiz.single_attempt is True and self.filter(user=user,
                                                       quiz=quiz,
                                                       complete=True)\
                                               .exists():
            return False

        try:
            sitting = self.get(user=user, quiz=quiz, complete=False)
        except Sitting.DoesNotExist:
            sitting = self.new_sitting(user, quiz)
        except Sitting.MultipleObjectsReturned:
            sitting = self.filter(user=user, quiz=quiz, complete=False)[0]
        return sitting


class Sitting(models.Model):
    """
    Used to store the progress of logged in users sitting a quiz.
    Replaces the session system used by anon users.

    Question_order is a list of integer pks of all the questions in the
    quiz, in order.

    Question_list is a list of integers which represent id's of
    the unanswered questions in csv format.

    Incorrect_questions is a list in the same format.

    Sitting deleted when quiz finished unless quiz.exam_paper is true.

    User_answers is a json object in which the question PK is stored
    with the answer the user gave.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("User"))

    quiz = models.ForeignKey(Quiz, verbose_name=_("Quiz"))

    question_order = models.CommaSeparatedIntegerField(
        max_length=1024, verbose_name=_("Question Order"))

    question_list = models.CommaSeparatedIntegerField(
        max_length=1024, verbose_name=_("Question List"))

    incorrect_questions = models.CommaSeparatedIntegerField(
        max_length=1024, blank=True, verbose_name=_("Incorrect questions"))

    current_score = models.IntegerField(verbose_name=_("Current Score"))

    complete = models.BooleanField(default=False, blank=False,
                                   verbose_name=_("Complete"))

    user_answers = models.TextField(blank=True, default='{}',
                                    verbose_name=_("User Answers"))

    start = models.DateTimeField(auto_now_add=True,
                                 verbose_name=_("Start"))
    current_question = models.IntegerField(verbose_name=_("Current Question"
                                                          "Number"),
                                           default=0)

    total_questions = models.IntegerField(verbose_name=_("Total Number"
                                                         "of Questions"))

    end = models.DateTimeField(null=True, blank=True, verbose_name=_("End"))

    objects = SittingManager()

    class Meta:
        permissions = (("view_sittings", _("Can see completed exams.")),)

    def get_first_question(self):
        #import pdb;pdb.set_trace()
        """
        Returns the next question.
        If no question is found, returns False
        Does NOT remove the question from the front of the list.
        """
        if self.total_questions < self.current_question:
            return False
        # first, _ = self.question_list.split(',', 1)
        
        first = self.question_order.split(',')[self.current_question]
        question_id = int(first) 
        
        return Question.objects.get_subclass(id=question_id)

    def remove_first_question(self):
        if not self.question_list:
            return

        _, others = self.question_list.split(',', 1)
        self.question_list = others
        self.save()

    # def add_to_score(self, points):
    #     self.current_score += int(points)
    #     self.save()

    @property
    def get_current_score(self):
        return self.current_score

    def _question_ids(self):
        return [int(n) for n in self.question_order.split(',') if n]

    @property
    def get_percent_correct(self):
        dividend = float(self.current_score)
        divisor = len(self._question_ids())
        if divisor < 1:
            return 0            # prevent divide by zero error

        if dividend > divisor:
            return 100

        correct = int(round((dividend / divisor) * 100))

        if correct >= 1:
            return correct
        else:
            return 0

    def mark_quiz_complete(self):
        self.complete = True
        self.end = now()
        self.save()

    def end_quiz(self):
        user_answers = json.loads(self.user_answers)
        total_correct = 0
        for question_id in user_answers:
            if(user_answers[question_id][1] == 'True'):
                total_correct += 1
        passedattempt = 0
        if(self.quiz.pass_mark <= ((total_correct) / (self.total_questions + 1)) * 100):
            passedattempt = 1
        if(Progress.objects.filter(quiz=self.quiz, user=self.user).exists()):
            #  modify existing
            current_progress = Progress.objects.filter(quiz=self.quiz, user=self.user)[0]
            best_score_ = current_progress.best_score
            answers_of_best_attempt_ = current_progress.answers_of_best_attempt
            if(current_progress.best_score < total_correct):
                best_score_ = total_correct
                answers_of_best_attempt_ = self.user_answers
            Progress.objects.filter(quiz=self.quiz,
                                    user=self.user).update(attempts=current_progress.attempts + 1,
                                                           passed_attempts=current_progress.passed_attempts + passedattempt,
                                                           best_score=best_score_,
                                                           answers_of_best_attempt=answers_of_best_attempt_)
        else:
            #  insert all values newly
            progress_obj = Progress(user=self.user,
                                    quiz=self.quiz,
                                    attempts=1,
                                    passed_attempts=passedattempt,
                                    best_score=total_correct,
                                    quiz_maximum_marks=(self.total_questions+1),
                                    answers_of_best_attempt=self.user_answers)
            progress_obj.save()

    # def add_incorrect_question(self, question):
    #     """
    #     Adds uid of incorrect question to the list.
    #     The question object must be passed in.
    #     """
    #     if len(self.incorrect_questions) > 0:
    #         self.incorrect_questions += ','
    #     self.incorrect_questions += str(question.id) + ","
    #     if self.complete:
    #         self.add_to_score(-1)
    #     self.save()

    # @property
    # def get_incorrect_questions(self):
    #     """
    #     Returns a list of non empty integers, representing the pk of
    #     questions
    #     """
    #     return [int(q) for q in self.incorrect_questions.split(',') if q]

    # def remove_incorrect_question(self, question):
    #     current = self.get_incorrect_questions
    #     current.remove(question.id)
    #     self.incorrect_questions = ','.join(map(str, current))
    #     self.add_to_score(1)
    #     self.save()

    @property
    def check_if_passed(self):
        return self.get_percent_correct >= self.quiz.pass_mark

    @property
    def result_message(self):
        if self.check_if_passed:
            return self.quiz.success_text
        else:
            return self.quiz.fail_text

    def add_user_answer(self, question, guess, isCorrect, testCorrect):
        """
        isCorrect is True if question is correct
        testCorrect is 1 if Sample tests are cleared and -1 for multiple choice
        or true false questions.
        """
        current = json.loads(self.user_answers)
        current[str(question.id)] = [guess, isCorrect, testCorrect]
        self.user_answers = json.dumps(current)
        self.save()

    def get_questions(self, with_answers=False):
        question_ids = self._question_ids()
        questions = sorted(
            self.quiz.question_set.filter(id__in=question_ids)
                                  .select_subclasses(),
            key=lambda q: question_ids.index(q.id))

        # if with_answers:
        #     user_answers = json.loads(self.user_answers)
        #     for question in questions:
        #         question.user_answer = user_answers[str(question.id)]
        return questions

    @property
    def questions_with_user_answers(self):
        return {
            q: q.user_answer for q in self.get_questions(with_answers=True)
        }

    @property
    def get_max_score(self):
        return len(self._question_ids())

    def progress(self):
        """
        Returns the number of questions answered so far and the total number of
        questions.
        """
        answered = len(json.loads(self.user_answers))
        total = self.get_max_score
        return answered, total


class QuestionType(models.Model):
    ques_type = models.CharField(max_length=50,
                                 verbose_name="Type Of Question")

    def __unicode__(self):
        return self.ques_type

    def __str__(self):
        return self.ques_type


@python_2_unicode_compatible
class Question(models.Model):
    """
    Base class for all question types.
    Shared properties placed here.
    """

    quiz = models.ManyToManyField(Quiz,
                                  verbose_name=_("Quiz"),
                                  blank=True)
    question_type = models.ForeignKey(QuestionType,
                                      verbose_name=_("Question Type"),
                                      blank=True)
    category = models.ForeignKey(Category,
                                 verbose_name=_("Category"),
                                 blank=True,
                                 null=True)
    mark_allotted = models.PositiveIntegerField(
        verbose_name=_("Marks"),
        help_text=_("Marks allotted for this question."))

    tag = models.ManyToManyField(Tag, verbose_name=("Tag"), blank=True,
                                 null=True)

    sub_category = models.ForeignKey(SubCategory,
                                     blank=False,
                                     help_text=_("Enter the difficulty level"
                                                 "of the question"),
                                     verbose_name=_('sub_category'))

    figure = models.ImageField(upload_to='uploads/%Y/%m/%d',
                               blank=True,
                               null=True,
                               verbose_name=_("Figure"))

    content = models.TextField(max_length=2000,
                               blank=False,
                               help_text=_("Enter the question text that "
                                           "you want displayed"),
                               verbose_name=_('Question'))

    explanation = models.TextField(max_length=2000,
                                   blank=True,
                                   help_text=_("Explanation to be shown "
                                               "after the question has "
                                               "been answered."),
                                   verbose_name=_('Explanation'))

    objects = InheritanceManager()

    class Meta:
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")
        ordering = ['category']

    def __str__(self):
        return self.content
