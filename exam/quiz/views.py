"""This view is responsible for all the things for url /quiz/.

Here all the quiz based things are handled.

"""
import json
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, ListView, TemplateView, FormView

from .forms import QuestionForm
from .models import Quiz, Category, Progress, Sitting, Question
#  response coming from compile api


class QuizMarkerMixin(object):
    @method_decorator(login_required)
    @method_decorator(permission_required('quiz.view_sittings'))
    def dispatch(self, *args, **kwargs):
        return super(QuizMarkerMixin, self).dispatch(*args, **kwargs)


class SittingFilterTitleMixin(object):
    def get_queryset(self):
        queryset = super(SittingFilterTitleMixin, self).get_queryset()
        quiz_filter = self.request.GET.get('quiz_filter')
        if quiz_filter:
            queryset = queryset.filter(quiz__title__icontains=quiz_filter)
        return queryset


class QuizListView(ListView):
    model = Quiz

    def get_queryset(self):
        queryset = super(QuizListView, self).get_queryset()
        return queryset.filter(draft=False)


class QuizDetailView(DetailView):
    model = Quiz
    slug_field = 'url'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.draft and not request.user.has_perm('quiz.change_quiz'):
            raise PermissionDenied

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


class CategoriesListView(ListView):
    model = Category


class ViewQuizListByCategory(ListView):
    model = Quiz
    template_name = 'view_quiz_category.html'

    def dispatch(self, request, *args, **kwargs):
        self.category = get_object_or_404(
            Category,
            category=self.kwargs['category_name']
        )

        return super(ViewQuizListByCategory, self).\
            dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ViewQuizListByCategory, self)\
            .get_context_data(**kwargs)

        context['category'] = self.category
        return context

    def get_queryset(self):
        queryset = super(ViewQuizListByCategory, self).get_queryset()
        return queryset.filter(category=self.category, draft=False)


class QuizUserProgressView(TemplateView):
    template_name = 'progress.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(QuizUserProgressView, self)\
            .dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(QuizUserProgressView, self).get_context_data(**kwargs)
        progress, c = Progress.objects.get_or_create(user=self.request.user, quiz=self.quiz)
        context['cat_scores'] = progress.list_all_cat_scores
        context['exams'] = progress.show_exams()
        return context


class QuizMarkingList(QuizMarkerMixin, SittingFilterTitleMixin, ListView):
    model = Sitting

    def get_queryset(self):
        queryset = super(QuizMarkingList, self).get_queryset()\
                                               .filter(complete=True)

        user_filter = self.request.GET.get('user_filter')
        if user_filter:
            queryset = queryset.filter(user__username__icontains=user_filter)
        return queryset


class QuizMarkingDetail(QuizMarkerMixin, DetailView):
    model = Sitting

    def post(self, request, *args, **kwargs):
        sitting = self.get_object()
        q_to_toggle = request.POST.get('qid', None)
        if q_to_toggle:
            q = Question.objects.get_subclass(id=int(q_to_toggle))
        req_obj = self.get(request)
        return req_obj

    def get_context_data(self, **kwargs):
        context = super(QuizMarkingDetail, self).get_context_data(**kwargs)
        context['questions'] =\
            context['sitting'].get_questions(with_answers=True)
        return context

class NoQuestionException(Exception):
    pass


class QuizTake(FormView):
    form_class = QuestionForm
    template_name = 'question.html'

    def dispatch(self, request, *args, **kwargs):
        self.quiz = get_object_or_404(Quiz, url=self.kwargs['slug'])
        if self.quiz.draft and not request.user.has_perm('quiz.change_quiz'):
            raise PermissionDenied
        self.logged_in_user = self.request.user.is_authenticated()
        from .models import NoQuestionException
        if self.logged_in_user:
            try:
                self.sitting = Sitting.objects.user_sitting(request.user,
                                                       self.quiz)
            except NoQuestionException:
                return render(request, 'single_complete.html',{'allquestion_completed':True})
        # else:
        #     self.sitting = self.anon_load_sitting()
        else:
            raise PermissionDenied

        if self.sitting is False:
            return render(request, 'single_complete.html')

        return super(QuizTake, self).dispatch(request, *args, **kwargs)

    def get_form(self, form_class):
        if self.logged_in_user:
            self.question = self.sitting.get_first_question()
            self.progress = self.sitting.progress()
        # else:
        #     self.question = self.anon_next_question()
        #     self.progress = self.anon_sitting_progress()

        return form_class(**self.get_form_kwargs())

    def get_form_kwargs(self):
        kwargs = super(QuizTake, self).get_form_kwargs()
        return dict(kwargs, question=self.question)

    def form_valid(self, form):
        if self.logged_in_user:
            self.form_valid_user(form)
            if self.sitting.get_first_question() is False:
                return self.final_result_user()
        # else:
        #     self.form_valid_anon(form)
        #     if not self.request.session[self.quiz.anon_q_list()]:
        #         return self.final_result_anon()
        self.request.POST = {}

        return super(QuizTake, self).get(self, self.request)

    def get_context_data(self, **kwargs):
        # global compilebox_response
        context = super(QuizTake, self).get_context_data(**kwargs)
        context['question'] = self.question
        context['quiz'] = self.quiz
        #  context['tempCleared'] = self.sitting
        context['que_no'] = self.sitting.current_question
        context['total_questions'] = self.sitting.total_questions
        user_answers = json.loads(self.sitting.user_answers)
        if str(self.question.id) in user_answers:
            context['testcleared'] = user_answers[str(self.question.id)][-1]
            if(str(self.question.question_type) == "Coding"):
                context['user_code'] = user_answers[str(self.question.id)][0]
            else:
                if user_answers[str(self.question.id)][0] != "":
                    context['tot_radio_options'] = len(self.question.get_answers_list())
                    context['old_answer'] = user_answers[str(self.question.id)][0]
        context['questiontype'] = str(self.question.question_type)       
        return context

    def form_valid_user(self, form):
        guess = form.cleaned_data['answers']
        if(form.cleaned_data['buttontype'] == "Test"):
            if(guess == ""):
                return
            else:
                # check for sample case
                question_obj = CodingProb.objects.get(title=self.question)
                is_correct, response = self.question.check_if_test_correct(guess, question_obj)
                if is_correct is False:
                    self.sitting.add_user_answer(self.question, guess, "False", 0)
                    pass
                else:
                    #  Here need to increment score for the coding problem.
                    #  now calling up the next question
                    self.sitting.add_user_answer(self.question, guess, "False", 1)
                pass
        else:
            testcleared = -11
            try:
                question_obj = CodingProb.objects.get(title=self.question)
            except:
                question_obj = Question.objects.get(content=self.question)
            user_answers = json.loads(self.sitting.user_answers)
            if str(question_obj.id) in user_answers:
                testcleared = user_answers[str(self.question.id)][-1]
            if(guess == ""):
                if str(question_obj.question_type) == "Coding":
                    if str(self.question.id) in user_answers and user_answers[str(self.question.id)][1] is False:
                        if(testcleared == 1):
                            self.sitting.add_user_answer(self.question, guess, "False", 1)
                        else:
                            self.sitting.add_user_answer(self.question, guess, "False", 0)
                else:
                    #  for problems other then coding keeping value as -1
                    self.sitting.add_user_answer(self.question, guess,
                                                 "False", -1)
            else:
                if((form.cleaned_data['buttontype'] == "Previous" or
                   form.cleaned_data['buttontype'] == "Next") and
                   str(question_obj.question_type) == "Coding"):
                    if str(self.question.id) in user_answers and user_answers[str(self.question.id)][1] is False:
                        if(testcleared == 1):
                            self.sitting.add_user_answer(self.question, guess, "False", 1)
                        else:
                            self.sitting.add_user_answer(self.question, guess, "False", 0)
                else:
                    #  if there is any answer selected
                    is_correct = False
                    if str(question_obj.question_type) == "Coding":
                        #  do all processing specilly for the coding problem
                        is_correct, response = self.question.check_if_all_correct(guess, question_obj)
                        # compilebox_response = response
                        if is_correct is False:
                            #  Increment the users attempts.
                            self.sitting.add_user_answer(self.question, guess, "False", 1)
                        else:
                            self.sitting.add_user_answer(self.question, guess,
                                                         "True", 1)
                            #  if code got accepted

                            # if((self.sitting.current_question + 1) ==
                            #    self.sitting.total_questions + 1):
                            #     # finish the test
                            #     form.cleaned_data['buttontype'] = "EndTest"
                            # else:
                            #     form.cleaned_data['buttontype'] = "Next"
                    else:
                        #  doing all processing for multiple choice
                        #  and true false
                        is_correct = self.question.check_if_correct(guess)
                        if is_correct is True:
                            #  change here to add different
                            #  mark for different questions
                            self.sitting.add_user_answer(self.question, guess,
                                                         "True", -1)
                        else:
                            #  self.sitting.add_incorrect_question(self.question)
                            self.sitting.add_user_answer(self.question, guess,
                                                         "False", -1)
        if(form.cleaned_data['buttontype'] == "Next"):
            self.sitting.current_question += 1
            self.sitting.save()
        elif(form.cleaned_data['buttontype'] == "Previous"):
            if(self.sitting.current_question > 0):
                self.sitting.current_question -= 1
                self.sitting.save()
        elif(form.cleaned_data['buttontype'] == "EndTest"):
            self.sitting.end_quiz()
            self.sitting.current_question += self.sitting.total_questions + 5
            self.sitting.save()

    def final_result_user(self):
        #  Optimize in fututre
        user_answers = json.loads(self.sitting.user_answers)
        total_correct = 0
        for i in user_answers:
            if(user_answers[i][1] == 'True'):
                total_correct += 1
        _score = ((total_correct) / (self.sitting.total_questions + 1)) * 100
        score = float("{0:.2f}".format(_score))
        results = {
            'quiz': self.quiz,
            'score': total_correct,
            'max_score': self.sitting.total_questions + 1,
            'percent': score ,
            'sitting': self.sitting,
            'previous': {},
        }
        self.sitting.mark_quiz_complete()

        if self.quiz.answers_at_end:
            results['questions'] =\
                self.sitting.get_questions(with_answers=True)
            results['incorrect_questions'] = ""  # self.sitting.get_incorrect_questions

        if self.quiz.exam_paper is False:
            self.sitting.delete()
        return render(self.request, 'result.html', results)

#  keeping all the anonymous users functions here

    """
    def anon_load_sitting(self):
        if self.quiz.single_attempt is True:
            return False

        if self.quiz.anon_q_list() in self.request.session:
            return self.request.session[self.quiz.anon_q_list()]
        else:
            return self.new_anon_quiz_session()

    def new_anon_quiz_session(self):

        Sets the session variables when starting a quiz for the first time
        as a non signed-in user


        self.request.session.set_expiry(259200)  # expires after 3 days
        questions = self.quiz.get_questions()
        question_list = [question.id for question in questions]

        if self.quiz.random_order is True:
            random.shuffle(question_list)

        if self.quiz.max_questions and (self.quiz.max_questions
                                        < len(question_list)):
            question_list = question_list[:self.quiz.max_questions]

        # session score for anon users
        self.request.session[self.quiz.anon_score_id()] = 0

        # session list of questions
        self.request.session[self.quiz.anon_q_list()] = question_list

        # session list of question order and incorrect questions
        self.request.session[self.quiz.anon_q_data()] = dict(
            incorrect_questions=[],
            order=question_list,
        )

        return self.request.session[self.quiz.anon_q_list()]

    def anon_next_question(self):
        next_question_id = self.request.session[self.quiz.anon_q_list()][0]
        return Question.objects.get_subclass(id=next_question_id)

    def anon_sitting_progress(self):
        total = len(self.request.session[self.quiz.anon_q_data()]['order'])
        answered = total - len(self.request.session[self.quiz.anon_q_list()])
        return (answered, total)

    def form_valid_anon(self, form):
        guess = form.cleaned_data['answers']
        is_correct = self.question.check_if_correct(guess)

        if is_correct:
            self.request.session[self.quiz.anon_score_id()] += 1
            anon_session_score(self.request.session, 1, 1)
        else:
            anon_session_score(self.request.session, 0, 1)
            self.request\
                .session[self.quiz.anon_q_data()]['incorrect_questions']\
                .append(self.question.id)

        self.previous = {}
        if self.quiz.answers_at_end is not True:
            self.previous = {'previous_answer': guess,
                             'previous_outcome': is_correct,
                             'previous_question': self.question,
                             'answers': self.question.get_answers(),
                             'question_type': {self.question
                                               .__class__.__name__: True}}

        self.request.session[self.quiz.anon_q_list()] =\
            self.request.session[self.quiz.anon_q_list()][1:]

    def final_result_anon(self):
        score = self.request.session[self.quiz.anon_score_id()]
        q_order = self.request.session[self.quiz.anon_q_data()]['order']
        max_score = len(q_order)
        percent = int(round((float(score) / max_score) * 100))
        session, session_possible = anon_session_score(self.request.session)
        if score is 0:
            score = "0"

        results = {
            'score': score,
            'max_score': max_score,
            'percent': percent,
            'session': session,
            'possible': session_possible
        }

        del self.request.session[self.quiz.anon_q_list()]

        if self.quiz.answers_at_end:
            results['questions'] = sorted(
                self.quiz.question_set.filter(id__in=q_order)
                                      .select_subclasses(),
                key=lambda q: q_order.index(q.id))

            results['incorrect_questions'] = (
                self.request
                    .session[self.quiz.anon_q_data()]['incorrect_questions'])

        else:
            results['previous'] = self.previous

        del self.request.session[self.quiz.anon_q_data()]

        return render(self.request, 'result.html', results)

#  def anon_session_score(session, to_add=0, possible=0):

    Returns the session score for non-signed in users.
    If number passed in then add this to the running total and
    return session score.

    examples:
        anon_session_score(1, 1) will add 1 out of a possible 1
        anon_session_score(0, 2) will add 0 out of a possible 2
        x, y = anon_session_score() will return the session score
                                    without modification

    Left this as an individual function for unit testing
    """

    """
    if "session_score" not in session:
        session["session_score"], session["session_score_possible"] = 0, 0

    if possible > 0:
        session["session_score"] += to_add
        session["session_score_possible"] += possible

    return session["session_score"], session["session_score_possible"]
"""
