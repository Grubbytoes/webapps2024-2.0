from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db import transaction


## MODEL CLASSES

class UserAccount(AbstractUser):
    def balance_str(self) -> str:
        _holding = self.holding
        return "{:.2f} {}".format(_holding.balance, _holding.currency)

    def get_payments_made(self) -> int:
        return Transaction.objects.filter(sender__account=self).count()

    def get_payments_received(self) -> int:
        return Transaction.objects.filter(recipient__account=self).count()

    @staticmethod
    def user_by_name(name: str):
        queryset = UserAccount.objects.filter(username=name)
        try:
            return queryset[0]
        except IndexError:
            return None


CURRENCIES = {
    "USD": "American Dollar",
    "GBP": "Pound Sterling",
    "EUR": "Euro"
}


class Holding(models.Model):
    """
    The amount of money an account has
    """
    account = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    balance = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, choices=CURRENCIES, default="GBP")

    def send_payment(self, recipient: 'Holding', amount) -> bool:
        """
        Sends money, and saves the transaction as a log. does NOT check to see whether balance is sufficient,
        not negative etc.

        :param recipient:
        :param amount:
        :return:
        """

        success = False
        try:
            with transaction.atomic():
                # Transfer money
                self.balance -= amount
                self.save()
                recipient.balance += amount
                recipient.save()

                # Log the transaction
                t = Transaction(value=amount)
                t.sender = self
                t.recipient = recipient
                t.save()
                success = True
        finally:
            return success

    def send_request(self, recipient, amount):
        pass


class AbstractMoneyMovement(models.Model):
    sender = models.ForeignKey(Holding, name="sender", on_delete=models.CASCADE, related_name="sent_from")
    recipient = models.ForeignKey(Holding, name="recipient", on_delete=models.CASCADE, related_name="received_by")
    value = models.PositiveIntegerField(verbose_name="Value (as sent)")
    date_made = models.DateTimeField(auto_now_add=1)


class Request(AbstractMoneyMovement):
    STATUSES = {
        'PEN': 'pending',
        'ACC': 'accepted',
        'REJ': 'rejected',
        'WIT': 'withdrawn'
    }
    status = models.CharField(max_length=3, choices=STATUSES, default='PEN')


class Transaction(AbstractMoneyMovement):
    executed = models.BooleanField(default=False)
    requested = models.OneToOneField(Request, null=True, default=None, on_delete=models.SET_NULL)

# GLOBAL FUNCTIONS

def find_user_holding(user: AbstractUser) -> Holding | None:
    query = Holding.objects.filter(account=user)
    if query.exists():
        return query[0]
    else:
        return None
