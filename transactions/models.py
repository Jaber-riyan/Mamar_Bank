from django.db import models
from accounts.models import UserBankAccount
# Create your models here.
from .constants import TRANSACTION_TYPE

class Transaction(models.Model):
    account = models.ForeignKey(UserBankAccount, related_name = 'transactions', on_delete = models.CASCADE) # ekjon user er multiple transactions hote pare
    
    amount = models.DecimalField(decimal_places=2, max_digits = 12)
    balance_after_transaction = models.DecimalField(decimal_places=2, max_digits = 12)
    transaction_type = models.IntegerField(choices=TRANSACTION_TYPE, null = True)
    timestamp = models.DateTimeField(auto_now_add=True)
    loan_approve = models.BooleanField(default=False) 
    bankrupt = models.BooleanField(default=False,null=True,blank=True)
    
    class Meta:
        ordering = ['timestamp'] 
        
        
class MoneyTransfer(models.Model):
    user = models.ForeignKey(UserBankAccount,on_delete = models.CASCADE,null=True,blank=True)
    account_no = models.IntegerField()
    amount = models.IntegerField()
    
    # def __str__(self):
    #     return str(self.user.account_no)