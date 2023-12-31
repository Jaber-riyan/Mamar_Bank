from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms.models import BaseModelForm
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.http import HttpResponse
from django.views.generic import CreateView, ListView
from transactions.constants import DEPOSIT, WITHDRAWAL,LOAN, LOAN_PAID
from datetime import datetime
from django.db.models import Sum
from accounts import models
from django.core.mail import send_mail
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.http import Http404
from transactions.forms import (
    DepositForm,
    WithdrawForm,
    LoanRequestForm,
    TransferMoneyForm
)
from transactions.models import Transaction

def send_transaction_mail(subject,amount,user,message_type,template):
    mail_subject = subject
    message_body = render_to_string(template,{
        'message_type' : message_type,
        'user':user,
        'amount':amount,
    })
    # to_email = user.email
    send_email = EmailMultiAlternatives(mail_subject,'',to=[user.user.email])
    send_email.attach_alternative(message_body,"text/html")
    send_email.send()




class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = 'transactions/transaction_form.html'
    model = Transaction
    title = ''
    success_url = reverse_lazy('transaction_report')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) # template e context data pass kora
        context.update({
            'title': self.title
        })

        return context


class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposit'

    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
        # if not account.initial_deposit_date:
        #     now = timezone.now()
        #     account.initial_deposit_date = now
        account.balance += amount # amount = 200, tar ager balance = 0 taka new balance = 0+200 = 200
        account.save(
            update_fields=[
                'balance'
            ]
        )

        messages.success(
            self.request,
            f'{"{:,.2f}".format(float(amount))}$ was deposited to your account successfully. If Your fill form with valid Email Check Your Email'
        )
        
        send_transaction_mail("Deposite Message",amount,self.request.user,'Deposite',"transactions/deposite_mail.html")

        return super().form_valid(form)
        
    

class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money'
    
    
    
    def dispatch(self, request, *args, **kwargs): 
        account = models.UserBankAccount.objects.get(user=request.user)
        # transaction = Transaction.objects.filter(account = account)
        
        # if transaction.exists() :
        is_bankrupt_account = Transaction.objects.filter(bankrupt=True).exists()
        
        if is_bankrupt_account:
            messages.error(request,'Bank is bankrupt')
            send_transaction_mail("Bankrupt Message",0,request.user,"Withdrawl",'transactions/is_bankrupt.html')
            return redirect('home')
        
        return super().dispatch(request,*args,**kwargs)


    def get_initial(self):
        initial = {'transaction_type': WITHDRAWAL}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')

        self.request.user.account.balance -= form.cleaned_data.get('amount')
        # balance = 300
        # amount = 5000
        self.request.user.account.save(update_fields=['balance'])

        messages.success(
            self.request,
            f'Successfully withdrawn {"{:,.2f}".format(float(amount))}$ from your account. If Your fill form with valid Email Check Your Email'
        )
        
        send_transaction_mail("Withdrawl Message",amount,self.request.user,"Withdrawl",'transactions/deposite_mail.html')

        return super().form_valid(form)




class LoanRequestView(TransactionCreateMixin):
    form_class = LoanRequestForm
    title = 'Request For Loan'


    def get_initial(self):
        initial = {'transaction_type': LOAN}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transaction.objects.filter(
            account=self.request.user.account,transaction_type=3,loan_approve=True).count()
        if current_loan_count >= 3:
            return HttpResponse("You have cross the loan limits")
        else:
            messages.success(
                self.request,
                f'Loan request for {"{:,.2f}".format(float(amount))}$ submitted successfully. If Your fill form with valid Email Check Your Email'
            )
            
        send_transaction_mail("Loan Request Message",amount,self.request.user,"Loan Request",'transactions/loan_request_mail.html')
        

        return super().form_valid(form)
    
class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = 'transactions/transaction_report.html'
    model = Transaction
    balance = 0 # filter korar pore ba age amar total balance ke show korbe
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account=self.request.user.account
        )
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
            self.balance = Transaction.objects.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date
            ).aggregate(Sum('amount'))['amount__sum']
        else:
            self.balance = self.request.user.account.balance
       
        return queryset.distinct() # unique queryset hote hobe
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account
        })

        return context
    
        
class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        loan = get_object_or_404(Transaction, id=loan_id)
        print(loan)
        if loan.loan_approve:
            user_account = loan.account
                # Reduce the loan amount from the user's balance
                # 5000, 500 + 5000 = 5500
                # balance = 3000, loan = 5000
            if loan.amount < user_account.balance:
                user_account.balance -= loan.amount
                loan.balance_after_transaction = user_account.balance
                user_account.save()
                loan.loan_approved = True
                loan.transaction_type = LOAN_PAID
                loan.save()
                return redirect('loan_list')
            else:
                messages.error(
            self.request,
            f'Loan amount is greater than available balance'
        )

        return redirect('loan_list')


class LoanListView(LoginRequiredMixin,ListView):
    model = Transaction
    template_name = 'transactions/loan_request.html'
    context_object_name = 'loans' # loan list ta ei loans context er moddhe thakbe
    
    def get_queryset(self):
        user_account = self.request.user.account
        queryset = Transaction.objects.filter(account=user_account,transaction_type=3)
        print(queryset)
        return queryset
    
    
# class MoneyTransfer(LoginRequiredMixin,):
#     template_name = 'transactions/money_transfer.html'
#     form_class = TransferMoneyForm
#     success_url = reverse_lazy('home')
    
    
    
#     def form_valid(self,form):
#         account_no = form.cleaned_data.get('account_no')
#         amount = form.cleaned_data.get('amount')
#         print(account_no)
#         print(amount)
        
#         sender_account = models.UserBankAccount.objects.get(user=self.request.user)
#         receiver_acccount = None
        
#         try:
#             receiver_acccount = models.UserBankAccount.objects.get(id=account_no)
        
#         except models.UserBankAccount.DoesNotExist:
#             # raise Http404(f"Account with ID {account_no} does not exist.")
#             messages.error(self.request, 'Receiver Account not found')
#             return super().form_invalid(form)
            
        
#         if amount > sender_account.balance:
#             messages.error(self.request,'Amount is more than Your Account Balance')
        
#         else:
#             sender_account.balance -= amount
#             receiver_acccount.balance += amount
#             messages.success(self.request,f'${amount} Transfer Successfully')
#             sender_account.save()
#             receiver_acccount.save()
        

#         return super().form_valid(form)




from django.shortcuts import get_object_or_404
from django.views.generic.edit import FormView

class MoneyTransferView(LoginRequiredMixin, FormView):
    template_name = 'transactions/money_transfer.html'
    form_class = TransferMoneyForm
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        account_no = form.cleaned_data.get('account_no')
        amount = form.cleaned_data.get('amount')
        print(account_no)
        print(amount)
        

        # sender_account = get_object_or_404(models.UserBankAccount, user = self.request.user)
        sender_account = models.UserBankAccount.objects.get(user=self.request.user)
        receiver_account = models.UserBankAccount.objects.get(id=account_no)

        # try:
        #     # receiver_account = get_object_or_404(models.UserBankAccount, id = account_no )
        #     receiver_account = models.UserBankAccount.objects.get(id=account_no)
            
        # except models.UserBankAccount.DoesNotExist:
        #     messages.error(self.request, 'Receiver Account not found')
        #     return super().form_invalid(form)
        
        # print(sender_account.email)
        # print(receiver_account.user.email)

        if amount > sender_account.balance:
            messages.error(self.request, 'Amount is more than Your Account Balance')
            return super().form_valid(form)
        
        if receiver_account.DoesNotExist:
            messages.error(self.request,'Receiver Account not found')  
            return super().form_valid(form)  
        
        else:
            sender_account.balance -= amount
            receiver_account.balance += amount
            messages.success(self.request, f'${amount} Transfer Successfully')
            sender_account.save()
            receiver_account.save()

        return super().form_valid(form)

        
        
    
    
    
    
    