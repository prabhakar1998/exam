from django import forms
from django.forms.widgets import RadioSelect


class QuestionForm(forms.Form):
    def __init__(self, question, *args, **kwargs):
        super(QuestionForm, self).__init__(*args, **kwargs)
        if question is False:
            return
        choice_list = [x for x in question.get_answers_list()]
        self.fields["buttontype"] = forms.CharField(widget=forms.HiddenInput,
                                                    required=False)
        if question.ques_type() == "others":
            choice_list = [x for x in question.get_answers_list()]
            self.fields["answers"] = forms.ChoiceField(choices=choice_list,
                                                       widget=RadioSelect,
                                                       required=False)
        else:
            self.fields["answers"] = forms.CharField(widget=forms.HiddenInput,
                                                     required=False)
            self.fields["type"] = forms.CharField(widget=forms.HiddenInput,
                                                  required=False)
