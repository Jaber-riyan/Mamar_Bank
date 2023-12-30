from django.contrib import admin
from .views import send_transaction_mail

# from transactions.models import Transaction
from .models import Transaction
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['account', 'amount', 'balance_after_transaction', 'transaction_type', 'loan_approve','bankrupt']
    
    def save_model(self, request, obj, form, change):
        obj.account.balance += obj.amount
        obj.balance_after_transaction = obj.account.balance
        obj.account.save()
        send_transaction_mail("Loan Approval Message",obj.amount,obj.account,"Loan Approve",'transactions/admin_mail.html')
        super().save_model(request, obj, form, change)


